//! Saved-body reconstruction and hypothetical register pools; no new native code.
use super::*;
use serde_json::{Value as Json,json};
use sha2::{Digest,Sha256};

fn pools(plan:&Plan)->Vec<(usize,Vec<Option<u32>>)> {
    vec![(4,allocate(plan).unwrap()),
        (6,allocate_pool(plan,[3,15,16,17,22,23]).unwrap()),
        (8,allocate_pool(plan,[3,15,16,17,22,23,24,25]).unwrap()),
        (11,allocate_pool(plan,[3,15,16,17,22,23,24,25,26,27,28]).unwrap())]
}
fn spilled(plan:&Plan,assigned:&[Option<u32>],id:Id)->bool {
    let n=&plan.nodes[id];plan.live[id] && n.width>0 && n.width<=8 && assigned[id].is_none()
        && !matches!(n.value,Value::Constant(_)|Value::Input(_)|Value::Base(_)|Value::Write{..})
}
fn metrics(plan:&Plan,hits:&[u64],calls:u64)->Vec<Json> {
    pools(plan).into_iter().map(|(size,assigned)| {
        let mut definitions=0u64;let mut operands=0u64;let mut values=0;
        for (id,node) in plan.nodes.iter().enumerate() {
            if !plan.live[id] {continue;}
            if spilled(plan,&assigned,id) {values+=1;if let Some(pc)=node.pc {definitions+=hits[pc];}}
            if matches!(node.value,Value::Phi(_)) {continue;}
            if let Some(pc)=node.pc {for src in node.inputs() {
                if spilled(plan,&assigned,src) {operands+=hits[pc];}
            }}
        }
        for (pc,effect) in plan.effects.iter().enumerate() {
            let id=match effect {Effect::Assert{value,..}|Effect::Switch{value,..}|Effect::Return(value)=>Some(*value),_=>None};
            if let Some(id)=id {if spilled(plan,&assigned,id) {operands+=hits[pc];}}
        }
        let saved:std::collections::BTreeSet<u32>=assigned.iter().flatten().copied().filter(|r|*r>=22).collect();
        json!({"pool":size,"narrow_spill_values":values,"successful_spill_definitions":definitions,
            "successful_spill_ir_operands":operands,"saved_registers":saved,
            "hypothetical_successful_save_restore_instructions":2*saved.len() as u64*calls})
    }).collect()
}
fn spill_details(plan:&Plan,hits:&[u64])->Vec<Json> {
    let assigned=allocate(plan).unwrap();
    let mut blocks=vec![None;plan.nodes.len()];
    let mut uses=vec![std::collections::BTreeSet::new();plan.nodes.len()];
    let mut operands=vec![0u64;plan.nodes.len()];
    for (id,n) in plan.nodes.iter().enumerate() {if let Some(pc)=n.pc {blocks[id]=Some(plan.at[pc]);}}
    for (block,b) in plan.blocks.iter().enumerate() {for &id in &b.phis {blocks[id]=Some(block);}}
    for (id,n) in plan.nodes.iter().enumerate() {
        if !plan.live[id] {continue;}
        if let Value::Phi(parts)=&n.value {for &(pred,part) in parts {uses[part.value].insert(pred);}continue;}
        if let Some(pc)=n.pc {for id in n.inputs() {uses[id].insert(plan.at[pc]);operands[id]+=hits[pc];}}
    }
    for (pc,e) in plan.effects.iter().enumerate() {
        let id=match e {Effect::Assert{value,..}|Effect::Switch{value,..}|Effect::Return(value)=>Some(*value),_=>None};
        if let Some(id)=id {uses[id].insert(plan.at[pc]);operands[id]+=hits[pc];}
    }
    plan.nodes.iter().enumerate().filter(|(id,_)|spilled(plan,&assigned,*id)).map(|(id,n)| {
        let category=match &n.value {
            Value::Phi(_) if n.width==1=>"byte_phi",
            Value::Phi(_)=>"other_phi",
            _ if uses[id].iter().any(|b|Some(*b)!=blocks[id])=>"cross_block_computation",
            _=>"local_computation",
        };
        let parts=if let Value::Phi(parts)=&n.value {
            parts.iter().map(|(p,s)|json!({"predecessor":p,"source":s.value,"byte":s.byte,"size":s.size})).collect::<Vec<_>>()
        } else {vec![]};
        json!({"node":id,"category":category,"value":format!("{:?}",n.value),"width":n.width,"pc":n.pc,
            "definition_block":blocks[id],"use_blocks":uses[id],"successful_definition_hits":n.pc.map_or(0,|pc|hits[pc]),
            "successful_ir_operand_hits":operands[id],"phi_parts":parts})
    }).collect()
}
fn fixture(split:bool)->Plan {
    let mut code=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},
        Op::Local{dst:2,offset:8},Op::Load{dst:3,address:2,size:8}];
    for r in 4..10 {code.extend([Op::Imm{dst:14,value:r as u128},
        Op::Binary{dst:r,overflow:15,op:Binary::Add,a:1,b:14,bits:64,signed:false}]);}
    if split {code.push(Op::Jump{target:code.len()+1});}
    code.push(Op::Imm{dst:11,value:0});
    for r in 4..10 {code.push(Op::Binary{dst:11,overflow:15,op:Binary::Add,a:11,b:r,bits:64,signed:false});}
    code.extend([Op::Store{address:0,src:11,size:8},Op::Return]);
    let f=crate::Function{name:"register pressure".into(),frame_size:16,frame_align:8,registers:16,
        args:vec![crate::Slot{offset:0,size:8},crate::Slot{offset:8,size:8}],result:crate::Slot{offset:0,size:8},code};
    let p=crate::Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions:vec![f],
        data:vec![],statics:vec![],thread_locals:vec![]};crate::validate(&p).unwrap();
    let memory=crate::proof::memory_plan_for_call(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    crate::scalar_ir::lower(&p.functions[0],&memory,250_000).unwrap()
}
#[test]
fn hypothetical_extra_registers_reduce_same_block_spills() {
    let plan=fixture(false);let rows=metrics(&plan,&vec![3;plan.effects.len()],3);
    assert_eq!(allocate(&plan).unwrap(),allocate_pool(&plan,[3,15,16,17]).unwrap());
    assert!(rows[0]["successful_spill_definitions"].as_u64().unwrap()>rows[2]["successful_spill_definitions"].as_u64().unwrap());
    assert_eq!(rows[0]["hypothetical_successful_save_restore_instructions"],0);
    assert!(rows[2]["hypothetical_successful_save_restore_instructions"].as_u64().unwrap()>0);
}
#[test]
fn spill_partition_ignores_dead_operand_uses() {
    let mut plan=fixture(true);let hits=vec![3;plan.effects.len()];
    let prior=spill_details(&plan,&hits);
    let id=prior.iter().find(|r|r["category"]=="cross_block_computation").unwrap()["node"].as_u64().unwrap() as usize;
    plan.nodes.push(Node{value:Value::Unary{src:id,op:Unary::Not,bits:64},width:8,pc:Some(0)});
    plan.live.push(false);
    assert_eq!(prior,spill_details(&plan,&hits));
    let baseline=metrics(&plan,&hits,3).remove(0);
    assert_eq!(prior.iter().map(|r|r["successful_ir_operand_hits"].as_u64().unwrap()).sum::<u64>(),
        baseline["successful_spill_ir_operands"].as_u64().unwrap());
}
#[test]
fn hypothetical_extra_registers_preserve_cross_block_spills() {
    let plan=fixture(true);
    let details=spill_details(&plan,&vec![1;plan.effects.len()]);
    for (_,assigned) in pools(&plan) {for pc in [5,7,9,11,13,15] {
        let id=*plan.computations[pc].iter().find(|id|matches!(plan.nodes[**id].value,Value::Binary{overflow:false,..})).unwrap();
        assert!(plan.live[id] && assigned[id].is_none());
        assert_eq!(details.iter().find(|r|r["node"]==id).unwrap()["category"],"cross_block_computation");
    }}
}
fn checked(path:&str,digest:&str,limit:usize)->Vec<u8> {
    let data=std::fs::read(path).unwrap();assert!(data.len()<=limit);
    assert_eq!(format!("{:x}",Sha256::digest(&data)),digest);data
}
#[test]
#[ignore="Requires exact closed store-log profiles, artifacts and native bodies"]
fn observe_saved_scalar_register_pressure() {
    let inputs:Vec<Json>=serde_json::from_slice(&std::fs::read(std::env::var("SCALAR_PRESSURE_INPUT").unwrap()).unwrap()).unwrap();assert_eq!(inputs.len(),3);
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
            let hits:Vec<u64>=serde_json::from_value(profiles[id]["jit_scalar_hits"].clone()).unwrap();assert_eq!(hits.len(),f.code.len());
            let calls:u64=f.code.iter().zip(&hits).filter(|(op,_)|matches!(op,Op::Return)).map(|(_,h)|*h).sum();
            functions.push(json!({"function":id,"name":f.name,"native_bytes":bytes.len(),"stack_bytes":emitted.stack_bytes,
                "reachable_blocks":plan.reachable.iter().filter(|b|**b).count(),"successful_calls":calls,
                "native_sp_ldr64":emitted.words.iter().filter(|w|**w&0xffc003e0==0xf94003e0).count(),
                "native_sp_str64":emitted.words.iter().filter(|w|**w&0xffc003e0==0xf90003e0).count(),
                "pools":metrics(&plan,&hits,calls),"spilled_values":spill_details(&plan,&hits)}));
        }
        assert_eq!(input["expected_scalar_bodies"],reconstructed);
        cases.push(json!({"index":input["index"],"reconstructed_bodies":reconstructed,"functions":functions}));
    }
    let out=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("SCALAR_PRESSURE_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(out,&json!({"status":"passed","cases":cases,"guest_commands":0,"executable_code_publications":0,
        "scope":"Exact current native bodies. Hypothetical allocations only. Successful IR definition/operand occurrences, excluding phi-edge transfers, are not emitted instruction counts or speed estimates. Save/restore assumes each used extra register is saved/restored once per successful Call. Private failed attempts are excluded. Static SP loads/stores include logs/output and untaken paths."})).unwrap();
}
