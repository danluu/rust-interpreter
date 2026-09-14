use super::*;
use serde_json::{Value as Json,json};
use sha2::{Digest,Sha256};

fn spilled(plan:&Plan,assignment:&[Option<u32>],id:Id) -> bool {
    let n=&plan.nodes[id];plan.live[id] && n.width>0 && n.width<=8 && assignment[id].is_none()
        && !matches!(n.value,Value::Constant(_)|Value::Input(_)|Value::Base(_))
}
fn metrics(plan:&Plan,assignment:&[Option<u32>],hits:&[u64]) -> Json {
    let mut definitions=0u64;let mut operands=0u64;let mut values=0;
    for (id,node) in plan.nodes.iter().enumerate() {
        if !plan.live[id] {continue;}
        if spilled(plan,assignment,id) {values+=1;if let Some(pc)=node.pc {definitions+=hits[pc];}}
        if matches!(node.value,Value::Phi(_)) {continue;}
        if let Some(pc)=node.pc {for input in node.inputs() {if spilled(plan,assignment,input) {operands+=hits[pc];}}}
    }
    for (pc,effect) in plan.effects.iter().enumerate() {
        if let Effect::Assert{value,..}|Effect::Switch{value,..}|Effect::Return(value)=*effect {
            if spilled(plan,assignment,value) {operands+=hits[pc];}
        }
    }
    json!({"narrow_spill_values":values,"successful_spill_definitions":definitions,
        "successful_spill_ir_operands":operands,"assigned_values":assignment.iter().filter(|r|r.is_some()).count()})
}
fn checked(input:&Json,key:&str,limit:usize)->Vec<u8> {
    let bytes=std::fs::read(input[key].as_str().unwrap()).unwrap();assert!(bytes.len()<=limit);
    assert_eq!(format!("{:x}",Sha256::digest(&bytes)),input[format!("{key}_sha256")]);bytes
}

#[test]
#[ignore="Requires closed adopted profiles and exact scalar bodies; no guest run"]
fn observe_saved_global_register_scope() {
    let inputs:Vec<Json>=serde_json::from_slice(&std::fs::read(std::env::var("SCALAR_GLOBAL_INPUT").unwrap()).unwrap()).unwrap();
    assert_eq!(inputs.len(),3);let mut cases=vec![];
    for input in inputs {
        let p:crate::Program=bincode::deserialize(&checked(&input,"artifact",64*1024*1024)).unwrap();crate::validate(&p).unwrap();
        let profile:Json=serde_json::from_slice(&checked(&input,"profile",256*1024*1024)).unwrap();
        let mapping:Json=serde_json::from_slice(&checked(&input,"operations",256*1024*1024)).unwrap();
        let code=checked(&input,"code",16*1024*1024);assert_eq!(mapping["code_sha256"],input["code_sha256"]);
        assert_eq!(mapping["schema_version"],2);
        for key in ["complete","reconstructed_bytes_match","profiled"] {assert_eq!(mapping[key],true);}
        let profiles=profile["functions"].as_array().unwrap();assert_eq!(profiles.len(),p.functions.len());
        let mut functions=vec![];
        for saved in mapping["functions"].as_array().unwrap() {
            if saved["spans"][0]["kind"]!="scalar_leaf" {continue;}
            let id=saved["function"].as_u64().unwrap() as usize;let f=&p.functions[id];
            assert_eq!(saved["name"],f.name);assert_eq!(profiles[id]["name"],f.name);
            let memory=crate::proof::memory_plan(&p,id,&mut crate::proof::MAX_GLOBAL_WORK.clone());
            let plan=crate::scalar_ir::lower(f,&memory,250_000).unwrap();
            let emitted=emit_call(&plan,true).unwrap();let bytes:Vec<_>=emitted.words.iter().flat_map(|w|w.to_le_bytes()).collect();
            let start=saved["offset"].as_u64().unwrap() as usize;let end=saved["end"].as_u64().unwrap() as usize;
            assert_eq!(&code[start..end],bytes.as_slice(),"adopted scalar body {id}");
            let hits:Vec<u64>=serde_json::from_value(profiles[id]["jit_scalar_hits"].clone()).unwrap();assert_eq!(hits.len(),f.code.len());
            let calls:u64=f.code.iter().zip(&hits).filter(|(op,_)|matches!(op,Op::Return)).map(|(_,h)|*h).sum();
            let baseline=allocate(&plan).unwrap();let next=allocate_global(&plan);
            let (assignment,detail)=match next {
                Ok(a)=>(a.registers,json!({"selected":a.global_selected,"work":a.work,"candidates":a.candidates,
                    "baseline_weight":a.baseline_weight,"global_weight":a.global_weight})),
                Err(reason)=>(baseline.clone(),json!({"selected":false,"declined":reason})),
            };
            assert!(plan.nodes.iter().enumerate().filter(|(_,n)|matches!(n.value,Value::Phi(_))).all(|(id,_)|assignment[id].is_none()));
            functions.push(json!({"function":id,"name":f.name,"successful_calls":calls,"native_bytes":bytes.len(),
                "before":metrics(&plan,&baseline,&hits),"after":metrics(&plan,&assignment,&hits),"allocation":detail}));
        }
        assert_eq!(input["expected_scalar_bodies"],functions.len());
        cases.push(json!({"index":input["index"],"reconstructed_bodies":functions.len(),"functions":functions}));
    }
    let out=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("SCALAR_GLOBAL_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(out,&json!({"status":"passed","cases":cases,"guest_commands":0,"executable_code_publications":0,
        "scope":"Exact adopted scalar bodies. Test-only global allocation model. Successful IR definition/operand occurrences exclude phi-edge transfers and failed private attempts; they are not emitted instructions or time savings. No generated code or runtime policy change."})).unwrap();
}
