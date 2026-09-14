use super::*;
use crate::{Program,Slot,VERSION};
fn fixture(stores:usize)->Program {
    let mut code=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Imm{dst:2,value:19}];
    code.extend((0..stores).map(|_|Op::Store{address:1,src:2,size:8}));code.push(Op::Return);
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![0;64],thread_locals:vec![],
        functions:vec![Function{name:"transaction control".into(),frame_size:8,frame_align:8,registers:8,
            args:vec![Slot{offset:0,size:8}],result:Slot{offset:0,size:0},code}]}
}
#[test]
fn transaction_store_effects_are_live_and_production_admission_stays_closed() {
    let p=fixture(2);crate::validate(&p).unwrap();
    assert!(!crate::proof::memory_plan_for_call(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone()).eligible);
    let memory=crate::proof::memory_plan_transaction(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());assert!(memory.eligible);
    let plan=lower(&p.functions[0],&memory,250_000).unwrap();
    let stores:Vec<_>=plan.nodes.iter().enumerate().filter(|(_,n)|matches!(n.value,Value::Write{..})).collect();
    assert_eq!(stores.len(),2);assert!(stores.iter().all(|(i,_)|plan.live[*i]));
    for profiled in [false,true] {
        assert_eq!(native_leaf::emit(&plan,profiled).err(),Some("native_external_write_unimplemented"));
        assert_eq!(native_leaf::emit_call(&plan,profiled).err(),Some("native_external_write_unimplemented"));
    }
}
#[test]
fn transaction_store_count_width_unknown_effect_and_cycle_limits_remain_bounded() {
    let prove=|p:&Program|crate::proof::memory_plan_transaction(p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    assert!(prove(&fixture(16)).eligible);
    assert_eq!(prove(&fixture(17)).decline.unwrap().reason,"transaction_store_limit");
    assert!(!crate::proof::memory_plan_transaction(&fixture(1),0,&mut 0).eligible);
    let mut p=fixture(1);p.functions[0].code[3]=Op::FillBytes{address:1,value:2,size:2};
    assert!(!prove(&p).eligible); // 19-byte external fill exceeds the effect bound.
    p=fixture(1);p.functions[0].code[3]=Op::Allocate{dst:2,size:1,align:1,zeroed:true};assert!(!prove(&p).eligible);
    p=fixture(1);p.functions[0].code[4]=Op::Jump{target:3};
    assert_eq!(lower(&p.functions[0],&prove(&p),250_000).err(),Some("scalar_cycle"));
}
#[test]
#[ignore="Requires pinned public bytecode and a fresh output path"]
fn observe_saved_transaction_plans() {
    use serde_json::json;use sha2::{Digest,Sha256};
    let bytes=std::fs::read(std::env::var("TRANSACTION_ARTIFACT").unwrap()).unwrap();assert!(bytes.len()<=128*1024*1024);
    let digest=format!("{:x}",Sha256::digest(&bytes));assert_eq!(digest,std::env::var("TRANSACTION_ARTIFACT_SHA256").unwrap());
    let p:Program=bincode::deserialize(&bytes).unwrap();crate::validate(&p).unwrap();assert!(p.functions.len()<=65536);
    let mut work=crate::proof::MAX_GLOBAL_WORK;let mut scalar_work=128_000_000usize;let mut rows=vec![];
    for (id,f) in p.functions.iter().enumerate() {
        let memory=crate::proof::memory_plan_transaction(&p,id,&mut work);
        let limit=scalar_work.min(250_000);let plan=lower(f,&memory,limit);let summary=summary(&plan);
        scalar_work=scalar_work.saturating_sub(match &plan {Ok(p)=>p.work,Err("no_memory_plan")=>0,Err(_)=>limit});
        let reads=plan.as_ref().ok().map(|p|p.nodes.iter().filter(|n|matches!(n.value,Value::Read{..})).count()).unwrap_or(0);
        let writes=plan.as_ref().ok().map(|p|p.nodes.iter().filter(|n|matches!(n.value,Value::Write{..})).count()).unwrap_or(0);
        if let Ok(plan)=&plan {if writes>0 {assert_eq!(native_leaf::emit_call(plan,false).err(),Some("native_external_write_unimplemented"));}}
        rows.push(json!({"function":id,"name":f.name,"memory_eligible":memory.eligible,"memory_decline":memory.decline,
            "scalar":summary,"external_reads":reads,"external_writes":writes,"candidate":plan.is_ok() && writes>0,"native_implemented":false}));
    }
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("TRANSACTION_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","artifact_sha256":digest,"rows":rows,"functions":p.functions.len(),
        "memory_work_used":crate::proof::MAX_GLOBAL_WORK-work,"memory_work_remaining":work,
        "scalar_work_used":128_000_000-scalar_work,"scalar_work_remaining":scalar_work,
        "production_policy_changed":false,"original_project_guest_commands":0,"executable_code_publications":0})).unwrap();
}
