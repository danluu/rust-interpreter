//! Exact saved-body reconstruction; diagnostic opportunities, no policy change.
use super::*;
use serde_json::{Value as Json,json};
use sha2::{Digest,Sha256};

fn sites(plan:&Plan,layout:&Layout,hits:&[u64])->Vec<Json> {
    layout.sites.iter().enumerate().map(|(index,s)| {
        let pc=plan.nodes[s.id].pc.unwrap();let block=plan.at[pc];
        let prior=layout.sites[..index].iter().rev().find(|p| {
            let pp=plan.nodes[p.id].pc.unwrap();pp<pc && plan.at[pp]==block
                && matches!(relation(&layout.identities,**p,s.address,s.size),Relation::Contains(_))
        });
        // If the first write executes and the private Call succeeds, every
        // later effect in this block also executed. A later containing write
        // overwrites every earlier byte before any guest observer can run.
        let later=layout.sites[index+1..].iter().find(|p| {
            let pp=plan.nodes[p.id].pc.unwrap();pp>pc && plan.at[pp]==block
                && matches!(relation(&layout.identities,**p,s.address,s.size),Relation::Contains(_))
        });
        let logical_address_used=plan.nodes.iter().enumerate().any(|(id,n)| {
            if id<=s.id || !plan.live[id] {return false;}
            if let Value::Read{address,size}=n.value {matches!(relation(&layout.identities,*s,address,size),Relation::Unknown)} else {false}
        });
        json!({"node":s.id,"pc":pc,"size":s.size,"successful_visits":hits[pc],
            "prior_same_block_containing_store":prior.map(|s|s.id),"later_same_block_containing_store":later.map(|s|s.id),
            "high_lane_unneeded":s.size<=8,"logical_address_slot_unneeded":!logical_address_used})
    }).collect()
}
#[test]
fn store_cost_opportunities_require_same_block_containing_effects() {
    let f=crate::Function{name:"store costs".into(),frame_size:8,frame_align:8,registers:4,
        args:vec![crate::Slot{offset:0,size:8}],result:crate::Slot{offset:0,size:0},code:vec![
            Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Imm{dst:2,value:19},
            Op::Store{address:1,src:2,size:8},Op::Imm{dst:2,value:37},Op::Store{address:1,src:2,size:8},Op::Return]};
    let mut p=crate::Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions:vec![f],
        data:vec![],statics:vec![],thread_locals:vec![]};
    for split in [false,true] {
        if split {p.functions[0].code[4]=Op::Jump{target:5};}
        let memory=crate::proof::memory_plan_transaction(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
        let plan=crate::scalar_ir::lower(&p.functions[0],&memory,250_000).unwrap();let layout=Layout::new(&plan,&mut 0).unwrap().unwrap();
        let rows=sites(&plan,&layout,&[2;7]);assert_eq!(rows.len(),2);
        assert_eq!(rows[0]["later_same_block_containing_store"].is_null(),split);
        assert_eq!(rows[1]["prior_same_block_containing_store"].is_null(),split);
        assert!(rows[0]["prior_same_block_containing_store"].is_null());assert!(rows[1]["later_same_block_containing_store"].is_null());
        assert!(rows.iter().all(|r|r["high_lane_unneeded"]==true && r["logical_address_slot_unneeded"]==true));
    }
}
fn checked(path:&str,digest:&str,limit:usize)->Vec<u8> {
    let data=std::fs::read(path).unwrap();assert!(data.len()<=limit);
    assert_eq!(format!("{:x}",Sha256::digest(&data)),digest);data
}
#[test]
#[ignore="Requires exact closed candidate profiles, artifacts and native bodies"]
fn observe_saved_native_store_costs() {
    let inputs:Vec<Json>=serde_json::from_slice(&std::fs::read(std::env::var("TRANSACTION_COSTS_INPUT").unwrap()).unwrap()).unwrap();assert_eq!(inputs.len(),3);
    let mut cases=vec![];
    for input in inputs {
        let read=|key:&str,limit|checked(input[key].as_str().unwrap(),input[format!("{key}_sha256")].as_str().unwrap(),limit);
        let p:crate::Program=bincode::deserialize(&read("artifact",128*1024*1024)).unwrap();crate::validate(&p).unwrap();assert!(!p.statics.is_empty());
        let profile:Json=serde_json::from_slice(&read("profile",256*1024*1024)).unwrap();
        let mapping:Json=serde_json::from_slice(&read("operations",256*1024*1024)).unwrap();let code=read("code",16*1024*1024);
        assert_eq!(mapping["code_sha256"],input["code_sha256"]);assert_eq!(mapping["schema_version"],2);
        for key in ["complete","reconstructed_bytes_match","profiled"] {assert_eq!(mapping[key],true);}
        let profiles=profile["functions"].as_array().unwrap();assert_eq!(profiles.len(),p.functions.len());
        let mut functions=vec![];let mut reconstructed=0;
        for saved in mapping["functions"].as_array().unwrap() {
            if saved["spans"][0]["kind"]!="scalar_leaf" {continue;}
            let id=saved["function"].as_u64().unwrap() as usize;let f=&p.functions[id];assert_eq!(saved["name"],f.name);assert_eq!(profiles[id]["name"],f.name);
            let memory=crate::proof::memory_plan_transaction(&p,id,&mut crate::proof::MAX_GLOBAL_WORK.clone());
            let plan=crate::scalar_ir::lower(f,&memory,250_000).unwrap();let emitted=emit_call_transaction(&plan,true,true).unwrap();
            let bytes:Vec<u8>=emitted.words.iter().flat_map(|w|w.to_le_bytes()).collect();
            let start=saved["offset"].as_u64().unwrap() as usize;let end=saved["end"].as_u64().unwrap() as usize;assert_eq!(&code[start..end],bytes.as_slice());reconstructed+=1;
            let Some(layout)=Layout::new(&plan,&mut 0).unwrap() else {continue;};
            let hits:Vec<u64>=serde_json::from_value(profiles[id]["jit_scalar_hits"].clone()).unwrap();assert_eq!(hits.len(),f.code.len());
            let calls:u64=f.code.iter().zip(&hits).filter(|(op,_)|matches!(op,Op::Return)).map(|(_,h)|*h).sum();
            functions.push(json!({"function":id,"name":f.name,"native_bytes":bytes.len(),"stack_bytes":emitted.stack_bytes,
                "successful_calls":calls,"successful_instructions":hits.iter().sum::<u64>(),"stores":sites(&plan,&layout,&hits)}));
        }
        assert_eq!(input["expected_scalar_bodies"],reconstructed);
        cases.push(json!({"index":input["index"],"reconstructed_bodies":reconstructed,"functions":functions}));
    }
    let out=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("TRANSACTION_COSTS_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(out,&json!({"status":"passed","cases":cases,"guest_commands":0,"executable_code_publications":0,
        "scope":"Exact profiled native reconstruction. Successful-path store visits only; private failures and runtime savings are unmeasured. Opportunities require separate implementation and controls."})).unwrap();
}
