use super::*;
use serde_json::{Value as Json,json};
use sha2::{Digest,Sha256};

fn checked(input:&Json,key:&str,limit:usize)->Vec<u8> {
    let bytes=std::fs::read(input[key].as_str().unwrap()).unwrap();assert!(bytes.len()<=limit);
    assert_eq!(format!("{:x}",Sha256::digest(&bytes)),input[format!("{key}_sha256")]);bytes
}

#[test]
#[ignore="Requires closed archived store-log profiles and exact scalar bodies; no guest run"]
fn observe_saved_entry_guard_scope() {
    let inputs:Vec<Json>=serde_json::from_slice(&std::fs::read(std::env::var("SCALAR_ENTRY_INPUT").unwrap()).unwrap()).unwrap();
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
            let memory=crate::proof::memory_plan_transaction(&p,id,&mut crate::proof::MAX_GLOBAL_WORK.clone());
            let plan=crate::scalar_ir::lower(f,&memory,250_000).unwrap();
            let emitted=emit_call_transaction(&plan,true,true).unwrap();let bytes:Vec<_>=emitted.words.iter().flat_map(|w|w.to_le_bytes()).collect();
            let start=saved["offset"].as_u64().unwrap() as usize;let end=saved["end"].as_u64().unwrap() as usize;
            assert_eq!(&code[start..end],bytes.as_slice(),"archived store-log scalar body {id}");
            let hits:Vec<u64>=serde_json::from_value(profiles[id]["jit_scalar_hits"].clone()).unwrap();assert_eq!(hits.len(),f.code.len());
            let calls:u64=f.code.iter().zip(&hits).filter(|(op,_)|matches!(op,Op::Return)).map(|(_,h)|*h).sum();
            let simple=classify(&plan);let classification=dependencies::classify_dependencies(&plan);
            let mut reads=0u64;let mut writes=0u64;
            for (nid,node) in plan.nodes.iter().enumerate() {
                if !plan.live[nid] {continue;}
                match node.value {
                    Value::Read{..}=>reads+=hits[node.pc.unwrap()],
                    Value::Write{..}=>writes+=hits[node.pc.unwrap()],_=>{},
                }
            }
            functions.push(json!({"function":id,"name":f.name,"successful_calls":calls,"native_bytes":bytes.len(),
                "native_sha256":format!("{:x}",Sha256::digest(&bytes)),"eligible":classification.is_ok(),
                "simple_eligible":simple.is_ok(),"simple_decline":simple.as_ref().err(),"decline":classification.as_ref().err(),"entry_plan":classification.as_ref().ok(),
                "successful_read_occurrences":reads,"successful_write_occurrences":writes}));
        }
        assert_eq!(input["expected_scalar_bodies"],functions.len());
        cases.push(json!({"index":input["index"],"reconstructed_bodies":functions.len(),"functions":functions}));
    }
    let out=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("SCALAR_ENTRY_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(out,&json!({"status":"passed","cases":cases,"guest_commands":0,"executable_code_publications":0,
        "scope":"Exact archived store-log scalar bodies, not adopted native bodies. Static dependency entry obligations including potentially earlier-write disjointness; no memory/fault model or emitter integration. Successful IR memory occurrences exclude failed private attempts and are not emitted instructions or time savings. No guest execution or executable publication."})).unwrap();
}
