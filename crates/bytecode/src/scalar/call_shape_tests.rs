//! Typed metadata only. This observer emits no executable code and changes no policy.
use super::*;

#[test]
#[ignore="Requires the pinned public artifact and a fresh output path"]
fn observe_saved_call_shapes() {
    use serde_json::json;
    use sha2::{Digest,Sha256};
    let bytes=std::fs::read(std::env::var("SHAPES_ARTIFACT").unwrap()).unwrap();
    assert!(bytes.len()<=128*1024*1024);
    let digest=format!("{:x}",Sha256::digest(&bytes));
    assert_eq!(digest,std::env::var("SHAPES_ARTIFACT_SHA256").unwrap());
    let p:Program=bincode::deserialize(&bytes).unwrap();crate::validate(&p).unwrap();
    assert!(p.functions.len()<=65536);
    let mut remaining=MAX_GLOBAL_WORK;
    let mut rows=vec![];let mut calls=vec![];
    for (id,f) in p.functions.iter().enumerate() {
        let memory=memory_plan(&p,id,&mut remaining);
        let plan=crate::scalar_ir::lower(f,&memory,250_000);
        let summary=crate::scalar_ir::summary(&plan);
        let mut native=vec![];
        if let Ok(plan)=&plan {
            for profiled in [false,true] {
                native.push(match crate::scalar_ir::native_leaf::emit_call(plan,profiled) {
                    Ok(code)=>json!({"profiled":profiled,"eligible":true,"bytes":code.words.len()*4,
                        "stack_bytes":code.stack_bytes,"success_steps":code.success_steps}),
                    Err(reason)=>json!({"profiled":profiled,"eligible":false,"decline":reason}),
                });
            }
        }
        let reason=memory.decline.as_ref().map_or("eligible",|d|d.reason);
        let mut operations=std::collections::BTreeMap::<String,usize>::new();
        for (pc,op) in f.code.iter().enumerate() {
            // Rendered names aid inspection only; typed variants drive call identity.
            let rendered=format!("{op:?}");
            *operations.entry(rendered.split([' ','{']).next().unwrap().to_owned()).or_default()+=1;
            if let Op::Call{function,args,destination}=op {
                calls.push(json!({"caller":id,"pc":pc,"callee":function,"args":args,"destination":destination}));
            }
        }
        let decline_context=memory.decline.as_ref().map(|d| {
            (d.pc.saturating_sub(5)..f.code.len().min(d.pc.saturating_add(6)))
                .map(|pc|json!({"pc":pc,"rendered":format!("{:?}",f.code[pc])})).collect::<Vec<_>>()
        });
        rows.push(json!({"function":id,"name":f.name,
            "function_sha256":format!("{:x}",Sha256::digest(bincode::serialize(f).unwrap())),
            "frame_size":f.frame_size,"frame_align":f.frame_align,"registers":f.registers,
            "operations":f.code.len(),"operation_histogram":operations,"arguments":f.args,"result":f.result,
            "memory_reason":reason,"memory_eligible":memory.eligible,"memory_decline":memory.decline,
            "decline_context":decline_context,"scalar":summary,"native":native}));
    }
    let file=std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("SHAPES_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","artifact_sha256":digest,
        "functions":p.functions.len(),"rows":rows,"calls":calls,"memory_work_used":MAX_GLOBAL_WORK-remaining,
        "memory_work_remaining":remaining,"original_project_guest_commands":0,
        "executable_code_publications":0,"production_policy_changed":false})).unwrap();
}
