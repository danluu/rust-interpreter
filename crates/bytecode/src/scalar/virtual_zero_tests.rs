use super::*;
use crate::{Engine,Limits,Slot,VERSION};

fn program(code:Vec<Op>,frame:usize,args:Vec<Slot>,result:Slot)->Program {
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![Function{name:"virtual zero control".into(),frame_size:frame,frame_align:8,registers:4,args,result,code}]}
}
fn relaxed(p:&Program)->MemoryPlan {crate::validate(p).unwrap();memory_plan_virtual_zero(p,0,&mut MAX_GLOBAL_WORK.clone())}
fn strict(p:&Program)->MemoryPlan {crate::validate(p).unwrap();memory_plan(p,0,&mut MAX_GLOBAL_WORK.clone())}
fn compare(p:&Program,args:&[u128],budget:usize) {
    let m=relaxed(p);assert!(m.eligible,"{:?}",m.decline);
    let plan=crate::scalar_ir::lower(&p.functions[0],&m,250_000).unwrap();
    let scalar=plan.evaluate(args,16,budget,&p.functions[0].name);
    let vm=crate::execute_profiled(p,args,Limits{instructions:budget as u64,..Limits::default()},Engine::Interpreter);
    match (scalar,vm) {
        (Ok(s),Ok((v,profile)))=>{
            assert_eq!(s.value,v.value);assert_eq!(s.pcs.len() as u64,v.instructions);
            let mut hits=vec![0u64;p.functions[0].code.len()];for pc in s.pcs {hits[pc]+=1;}
            assert_eq!(hits,profile.functions[0].interpreted);
        },
        (Err(a),Err(b))=>assert_eq!(a,b),
        (a,b)=>panic!("scalar {a:?}, VM {b:?}"),
    }
    // Offline emission only: do not allocate or publish executable memory.
    assert!(!crate::scalar_ir::native_leaf::emit_call(&plan,false).unwrap().words.is_empty());
}

#[test]
fn virtual_zero_partial_results_keep_zero_padding_arguments_and_every_budget() {
    for written in [0,1,2,4] {
        let mut code=vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:u64::MAX as u128}];
        if written!=0 {code.push(Op::Store{address:0,src:1,size:written});}
        code.push(Op::Return);
        let p=program(code,16,vec![Slot{offset:8,size:8}],Slot{offset:0,size:16});
        assert_eq!(strict(&p).decline.unwrap().reason,"local_read_before_write");
        for input in [0,u64::MAX as u128,0x123456789abcdef0] {
            for budget in 0..=p.functions[0].code.len()+1 {compare(&p,&[input],budget);}
        }
        assert!(!strict(&p).eligible,"the production policy remains strict");
    }
}

#[test]
fn virtual_zero_cfg_join_retains_the_unwritten_arm_and_original_counts() {
    let p=program(vec![Op::Local{dst:0,offset:8},Op::Load{dst:1,address:0,size:8},
        Op::Switch{value:1,cases:vec![(0,6)],otherwise:3},Op::Local{dst:0,offset:0},
        Op::Imm{dst:2,value:0xab},Op::Store{address:0,src:2,size:1},Op::Return],
        16,vec![Slot{offset:8,size:8}],Slot{offset:0,size:8});
    assert!(!strict(&p).eligible);
    for input in [0,1,2] {for budget in 0..=8 {compare(&p,&[input],budget);}}
}

#[test]
fn virtual_zero_never_relaxes_external_effects_widths_bounds_or_work_limits() {
    let prefix=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8}];
    for effect in [Op::Load{dst:2,address:1,size:1},Op::Store{address:1,src:2,size:1},
        Op::Allocate{dst:2,size:1,align:1,zeroed:true}] {
        let mut code=prefix.clone();code.push(effect);code.push(Op::Return);
        let p=program(code,8,vec![],Slot{offset:0,size:0});
        assert!(!relaxed(&p).eligible);
    }
    let p=program(vec![Op::Local{dst:0,offset:8},Op::Load{dst:1,address:0,size:1},Op::Return],
        8,vec![],Slot{offset:0,size:0});assert!(!relaxed(&p).eligible);
    let mut p=program(vec![Op::Return],8,vec![],Slot{offset:0,size:8});
    assert!(!memory_plan_virtual_zero(&p,0,&mut 0).eligible);
    p.functions[0].result.size=3;assert!(!relaxed(&p).eligible);
    p.functions[0].result.size=8;p.functions[0].frame_size=513;assert!(!relaxed(&p).eligible);
}

#[test]
fn virtual_zero_still_declines_cycles_in_scalar_lowering_and_nested_calls() {
    let p=program(vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Jump{target:1}],
        8,vec![],Slot{offset:0,size:0});
    let m=relaxed(&p);assert!(m.eligible);
    assert_eq!(crate::scalar_ir::lower(&p.functions[0],&m,250_000).unwrap_err(),"scalar_cycle");
    let p=program(vec![Op::Call{function:0,args:vec![],destination:0},Op::Return],8,vec![],Slot{offset:0,size:0});
    assert_eq!(relaxed(&p).decline.unwrap().reason,"has_callee");
}

#[test]
#[ignore="Requires the pinned public artifact and a fresh census output path"]
fn observe_saved_virtual_zero_candidates() {
    use serde_json::json;
    use sha2::{Digest,Sha256};
    let bytes=std::fs::read(std::env::var("ZERO_ARTIFACT").unwrap()).unwrap();
    assert!(bytes.len()<=128*1024*1024);
    let digest=format!("{:x}",Sha256::digest(&bytes));
    assert_eq!(digest,std::env::var("ZERO_ARTIFACT_SHA256").unwrap());
    let p:Program=bincode::deserialize(&bytes).unwrap();crate::validate(&p).unwrap();
    assert!(p.functions.len()<=65536);
    let mut strict_work=MAX_GLOBAL_WORK;let mut relaxed_work=MAX_GLOBAL_WORK;
    let mut reasons=std::collections::BTreeMap::<String,usize>::new();
    let mut rows=vec![];let mut candidates=vec![false;p.functions.len()];
    for (id,f) in p.functions.iter().enumerate() {
        let old=memory_plan(&p,id,&mut strict_work);
        let reason=old.decline.as_ref().map_or("eligible",|d|d.reason);
        *reasons.entry(reason.into()).or_default()+=1;
        if reason!="local_read_before_write" {continue;}
        let relaxed=memory_plan_virtual_zero(&p,id,&mut relaxed_work);
        let plan=crate::scalar_ir::lower(f,&relaxed,250_000);
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
        candidates[id]=native.len()==2 && native.iter().all(|n|n["eligible"]==true);
        rows.push(json!({"function":id,"name":f.name,"frame_size":f.frame_size,"registers":f.registers,
            "operations":f.code.len(),"arguments":f.args,"result":f.result,"strict_decline":old.decline,
            "relaxed_eligible":relaxed.eligible,"relaxed_decline":relaxed.decline,"scalar":summary,
            "native":native,"candidate":candidates[id]}));
    }
    let mut calls=vec![];
    for (caller,f) in p.functions.iter().enumerate() {
        for (pc,op) in f.code.iter().enumerate() {
            if let Op::Call{function,..}=op {
                if candidates[*function] {calls.push(json!({"caller":caller,"pc":pc,"callee":function}));}
            }
        }
    }
    let file=std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("ZERO_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","artifact_sha256":digest,
        "functions":p.functions.len(),"strict_reasons":reasons,"candidates":candidates.iter().filter(|v|**v).count(),
        "rows":rows,"calls":calls,"strict_work_used":MAX_GLOBAL_WORK-strict_work,
        "relaxed_work_used":MAX_GLOBAL_WORK-relaxed_work,"original_project_guest_commands":0,
        "executable_code_publications":0,"production_policy_changed":false})).unwrap();
}
