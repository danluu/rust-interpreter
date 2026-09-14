//! Saved-code diagnostic only. No guest execution or emitter policy changes.
use super::*;
use std::collections::BTreeMap;
use serde_json::{Value as Json,json};
use sha2::{Digest,Sha256};

// A diagnostic identity for the low-usize address, not a valid-address proof.
// Stop at joins, narrowing casts, loads and unknown arithmetic. Offsets wrap
// exactly as u64 arithmetic; a later range optimization would need new guards.
fn address(plan:&Plan,mut id:Id)->(Id,u64) {
    let mut offset=0u64;
    for _ in 0..plan.nodes.len() {
        match &plan.nodes[id].value {
            Value::Cast{src,from:64,to:64,..}=>id=*src,
            Value::Pack(parts) if parts.len()==1 && parts[0].byte==0 && parts[0].size>=8=>id=parts[0].value,
            Value::Binary{a,b,op:Binary::Add,bits:64,overflow:false,..}=>{
                let pair=match (&plan.nodes[*a].value,&plan.nodes[*b].value) {
                    (_,Value::Constant(n))=>Some((*a,*n as u64)),
                    (Value::Constant(n),_)=>Some((*b,*n as u64)),_=>None,
                };
                if let Some((next,n))=pair {id=next;offset=offset.wrapping_add(n);} else {break;}
            },
            _=>break,
        }
    }
    (id,offset)
}
fn kind(value:&Value)->&'static str {
    match value {
        Value::Read{..}=>"read",Value::Write{..}=>"write",Value::Constant(_)=>"constant",Value::Input(_)=>"input",Value::Base(_)=>"base",
        Value::Pack(_)=>"pack",Value::Phi(_)=>"phi",Value::Binary{overflow:true,..}=>"overflow",
        Value::Binary{..}=>"binary",Value::Unary{..}=>"unary",Value::Cast{..}=>"cast",Value::Select{..}=>"select",
    }
}
fn checked_json(path:&str,digest:&str,limit:usize)->Json {
    let bytes=std::fs::read(path).unwrap();assert!(bytes.len()<=limit);
    assert_eq!(format!("{:x}",Sha256::digest(&bytes)),digest);
    serde_json::from_slice(&bytes).unwrap()
}
fn empty()->Plan {
    Plan{nodes:vec![],blocks:vec![],at:vec![],computations:vec![],effects:vec![],live:vec![],reachable:vec![],
        maximum_steps:0,success_steps:None,result_size:0,work:0}
}
#[test]
fn low_address_identity_keeps_wrap_and_stops_at_narrowing_joins_and_overflow() {
    let mut p=empty();
    let values=vec![Value::Input(0),Value::Constant(u64::MAX as u128),
        Value::Binary{a:0,b:1,op:Binary::Add,bits:64,signed:false,overflow:false},
        Value::Constant(2),Value::Binary{a:3,b:2,op:Binary::Add,bits:64,signed:false,overflow:false},
        Value::Cast{src:4,from:64,to:64,signed:true},
        Value::Pack(vec![Slice{value:5,byte:0,size:8}]),
        Value::Cast{src:6,from:64,to:32,signed:false},
        Value::Pack(vec![Slice{value:6,byte:1,size:8}]),
        Value::Phi(vec![(0,Slice{value:6,byte:0,size:8})]),
        Value::Binary{a:0,b:1,op:Binary::Add,bits:64,signed:false,overflow:true},
        Value::Read{address:6,size:8}];
    p.nodes=values.into_iter().map(|value|Node{value,width:8,pc:None}).collect();
    for i in 4..=6 {assert_eq!(address(&p,i),(0,1));}
    for i in 7..=11 {assert_eq!(address(&p,i),(i,0));}
    for base in [0u64,1,2,u64::MAX-1,u64::MAX] {
        let actual=base.wrapping_add(u64::MAX).wrapping_add(2);
        assert_eq!(base.wrapping_add(address(&p,6).1),actual);
    }
}

#[test]
#[ignore="Requires exact closed readonly candidate captures and original artifacts"]
fn observe_saved_readonly_body_shapes() {
    let inputs:Json=serde_json::from_slice(&std::fs::read(std::env::var("READONLY_SHAPES_INPUT").unwrap()).unwrap()).unwrap();
    let inputs=inputs.as_array().unwrap();assert_eq!(inputs.len(),3);let mut cases=vec![];
    for input in inputs {
        let artifact=std::fs::read(input["artifact"].as_str().unwrap()).unwrap();assert!(artifact.len()<=128*1024*1024);
        assert_eq!(format!("{:x}",Sha256::digest(&artifact)),input["artifact_sha256"].as_str().unwrap());
        let program:crate::Program=bincode::deserialize(&artifact).unwrap();crate::validate(&program).unwrap();
        let profile=checked_json(input["profile"].as_str().unwrap(),input["profile_sha256"].as_str().unwrap(),256*1024*1024);
        let mapping=checked_json(input["operations"].as_str().unwrap(),input["operations_sha256"].as_str().unwrap(),256*1024*1024);
        let old=checked_json(input["control_operations"].as_str().unwrap(),input["control_operations_sha256"].as_str().unwrap(),256*1024*1024);
        let code=std::fs::read(input["code"].as_str().unwrap()).unwrap();assert!(code.len()<=16*1024*1024);
        let digest=format!("{:x}",Sha256::digest(&code));assert_eq!(digest,input["code_sha256"].as_str().unwrap());
        assert_eq!(mapping["code_sha256"],digest);assert_eq!(mapping["schema_version"],2);
        for m in [&mapping,&old] {assert_eq!(m["complete"],true);assert_eq!(m["reconstructed_bytes_match"],true);assert_eq!(m["profiled"],true);}
        let old_scalars:std::collections::BTreeSet<usize>=old["functions"].as_array().unwrap().iter()
            .filter(|f|f["spans"][0]["kind"]=="scalar_leaf").map(|f|f["function"].as_u64().unwrap() as usize).collect();
        let functions=profile["functions"].as_array().unwrap();assert_eq!(functions.len(),program.functions.len());
        // Jit::new_inner always enables the heap ABI for nonempty statics.
        // These three bound artifacts all satisfy that sufficient condition.
        assert!(!program.statics.is_empty());let heap=true;
        let mut rows=vec![];
        for saved in mapping["functions"].as_array().unwrap() {
            if saved["spans"][0]["kind"]!="scalar_leaf" {continue;}
            assert_eq!(saved["spans"].as_array().unwrap().len(),1);
            let id=saved["function"].as_u64().unwrap() as usize;let f=&program.functions[id];
            assert_eq!(saved["name"],f.name);assert_eq!(functions[id]["name"],f.name);
            let hits:Vec<u64>=serde_json::from_value(functions[id]["jit_scalar_hits"].clone()).unwrap();assert_eq!(hits.len(),f.code.len());
            let mut remaining=crate::proof::MAX_GLOBAL_WORK;
            let memory=crate::proof::memory_plan_for_call(&program,id,&mut remaining);
            let plan=crate::scalar_ir::lower(f,&memory,250_000).unwrap();let emitted=emit_call_with_heap(&plan,true,heap).unwrap();
            let start=saved["offset"].as_u64().unwrap() as usize;let end=saved["end"].as_u64().unwrap() as usize;
            let bytes:Vec<u8>=emitted.words.iter().flat_map(|w|w.to_le_bytes()).collect();assert_eq!(&code[start..end],bytes.as_slice());
            let mut nodes=BTreeMap::<&str,usize>::new();let mut weighted=BTreeMap::<&str,u64>::new();let mut reads=vec![];
            let mut prior=BTreeMap::new();let mut families=BTreeMap::<(usize,Id),Vec<usize>>::new();let mut aliases=vec![];
            for (node,n) in plan.nodes.iter().enumerate() {
                if !plan.live[node] {continue;}*nodes.entry(kind(&n.value)).or_default()+=1;
                if let Some(pc)=n.pc {*weighted.entry(kind(&n.value)).or_default()+=hits[pc];}
                if let Value::Cast{src,from,to,..}=&n.value {
                    if from==to {aliases.push(json!({"node":node,"src":src,"kind":"same_width_cast","visits":n.pc.map(|pc|hits[pc]).unwrap_or(0)}));}
                }
                if let Value::Read{address:source,size}=&n.value {
                    let pc=n.pc.unwrap();let block=plan.at[pc];let (root,offset)=address(&plan,*source);
                    let duplicate=prior.insert((block,root,offset,*size),node);
                    let index=reads.len();families.entry((block,root)).or_default().push(index);
                    reads.push(json!({"node":node,"pc":pc,"address":source,"root":root,"offset":offset,"size":size,
                        "successful_visits":hits[pc],"same_block_duplicate":duplicate}));
                }
            }
            let families:Vec<Json>=families.into_iter().filter(|(_,r)|r.len()>1).map(|((block,root),indices)|json!({"block":block,"root":root,"reads":indices})).collect();
            let calls:u64=f.code.iter().zip(&hits).filter(|(op,_)|matches!(op,crate::Op::Return)).map(|(_,hits)|*hits).sum();
            rows.push(json!({"function":id,"name":f.name,"new_body":!old_scalars.contains(&id),"frame_size":f.frame_size,
                "operations":f.code.len(),"successful_calls":calls,"successful_instructions":hits.iter().sum::<u64>(),
                "native_bytes":bytes.len(),"native_stack_bytes":emitted.stack_bytes,"native_register_values":emitted.register_values,
                "proof_work":memory.work,"scalar_work":plan.work,"live_nodes":nodes,"successful_computations":weighted,
                "reads":reads,"same_block_address_families":families,"aliases":aliases}));
        }
        cases.push(json!({"index":input["index"],"functions":rows}));
    }
    let out=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("READONLY_SHAPES_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(out,&json!({"status":"passed","cases":cases,"guest_commands":0,"executable_code_publications":0,
        "scope":"Exact reconstruction and successful scalar path counts. Static code sizes and address families are diagnostic opportunities, not timing or valid-address proofs; private failed attempts are not counted."})).unwrap();
}
