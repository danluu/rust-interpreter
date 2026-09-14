use super::*;
use serde_json::{json,Value as Json};
use sha2::{Digest,Sha256};

fn checked(input:&Json,key:&str,limit:usize)->Vec<u8> {
    let bytes=std::fs::read(input[key].as_str().unwrap()).unwrap();assert!(bytes.len()<=limit);
    assert_eq!(format!("{:x}",Sha256::digest(&bytes)),input[format!("{key}_sha256")]);bytes
}

#[test]
#[ignore="Requires exact closed public metadata and aggregate candidates; no guest execution"]
fn observe_saved_aggregate_projections() {
    let input:Json=serde_json::from_slice(&std::fs::read(std::env::var("SCALAR_AGGREGATE_INPUT").unwrap()).unwrap()).unwrap();
    let program:crate::Program=bincode::deserialize(&checked(&input,"artifact",64*1024*1024)).unwrap();crate::validate(&program).unwrap();
    let typed:Json=serde_json::from_slice(&checked(&input,"typed",64*1024*1024)).unwrap();
    assert_eq!(typed["artifact_sha256"],input["artifact_sha256"]);
    assert_eq!(typed["rows"].as_array().unwrap().len(),program.functions.len());
    let ids:Vec<usize>=serde_json::from_value(input["candidates"].clone()).unwrap();
    assert_eq!(ids.len(),132);assert!(ids.windows(2).all(|p|p[0]<p[1]));
    let mut policies=vec![];
    for zeroed in [false,true] {
        let mut remaining=crate::proof::MAX_GLOBAL_WORK;let mut lowering_remaining=256_000_000usize;let mut rows=vec![];
        for &id in &ids {
            let f=&program.functions[id];let prior=&typed["rows"][id];assert_eq!(prior["function"],id);
            assert_eq!(prior["name"],f.name);assert_eq!(prior["frame_size"],f.frame_size);
            assert_eq!(prior["registers"],f.registers);assert_eq!(prior["operations"],f.code.len());
            assert_eq!(prior["arguments"],serde_json::to_value(&f.args).unwrap());assert_eq!(prior["result"],serde_json::to_value(&f.result).unwrap());
            let memory=crate::proof::aggregate_memory_plan(&program,id,&mut remaining,zeroed);
            let mut row=json!({"function":id,"name":f.name,"frame_size":f.frame_size,"registers":f.registers,"result_size":f.result.size,
                "memory_eligible":memory.eligible,"memory_decline":memory.decline,"memory_work":memory.work});
            if memory.eligible {
                // Charge the complete per-function lowering allowance even on
                // an early decline; diagnostic traversal cannot evade its bound.
                let aggregate=if lowering_remaining<1_000_000 {Err("aggregate_global_work_limit")}
                    else {lowering_remaining-=1_000_000;Aggregate::new(f,&memory,1_000_000)};
                match aggregate {
                    Err(reason)=>{row["ir_eligible"]=json!(false);row["ir_decline"]=json!(reason);},
                    Ok(aggregate)=>{
                        row["ir_eligible"]=json!(true);row["ir_work"]=json!(aggregate.work);
                        let mut lanes=vec![];
                        for (size,plan) in aggregate.lanes {
                            // Emission produces a Vec of words only. No code
                            // allocation/publication, Call or guest run occurs.
                            let native=native_leaf::emit_call(&plan,false);
                            lanes.push(json!({"size":size,"ir":summary(&Ok(plan)),"native_eligible":native.is_ok(),
                                "native_decline":native.as_ref().err(),"native_bytes":native.as_ref().ok().map(|n|n.words.len()*4)}));
                        }
                        row["all_lanes_native"]=json!(lanes.iter().all(|l|l["native_eligible"]==true));
                        row["lanes"]=json!(lanes);
                    },
                }
            }
            rows.push(row);
        }
        policies.push(json!({"zeroed_frame":zeroed,"memory_work_remaining":remaining,"lowering_allowance_remaining":lowering_remaining,"rows":rows}));
    }
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("SCALAR_AGGREGATE_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","candidates":ids.len(),"policies":policies,
        "guest_commands":0,"executable_code_publications":0,"scope":"Typed confined-memory and per-lane IR/native-expression eligibility. Projected native words remain data. No combined computation, aggregate ABI, original guest execution, timing or adoption."})).unwrap();
}
