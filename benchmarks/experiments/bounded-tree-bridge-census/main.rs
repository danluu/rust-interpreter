//! Exact existing tree planner on validated saved code; no generated execution.
pub use rust_interp_bytecode::*;
use serde_json::json;
use std::collections::BTreeMap;

include!(concat!(env!("OUT_DIR"),"/support.rs"));
#[path="../../../crates/bytecode/src/jit/trees.rs"] mod trees;

fn main() {
    let args:Vec<_>=std::env::args_os().collect();assert_eq!(args.len(),3);
    assert!(std::fs::metadata(&args[1]).unwrap().len()<=128*1024*1024);
    let bytes=std::fs::read(&args[1]).unwrap();assert!(bytes.len()<=128*1024*1024);
    let p:Program=bincode::deserialize(&bytes).unwrap();validate(&p).unwrap();
    assert!(p.functions.len()<=65536);
    assert!(p.functions.iter().map(|f|f.code.len()).sum::<usize>()<=2_000_000);
    let plans=trees::analyze(&p);
    let rows:Vec<_>=p.functions.iter().enumerate().map(|(id,f)| {
        let (plan,decline)=match plans[id] {
            Ok(plan)=>(json!({"instructions":plan.instructions,"depth":plan.depth,"frame_span":plan.frame_span,
                "register_slots":plan.register_slots,"frame_align":plan.frame_align}),None),
            Err(reason)=>(serde_json::Value::Null,Some(format!("{reason:?}"))),
        };
        let calls:Vec<_>=f.code.iter().enumerate().filter_map(|(pc,op)|match op {
            Op::Call {function,..}=>Some(json!({"pc":pc,"callee":function})),_=>None,
        }).collect();
        json!({"function":id,"name":f.name,"frame_size":f.frame_size,"registers":f.registers,
            "bytecode_operations":f.code.len(),"plan":plan,"decline":decline,"calls":calls})
    }).collect();
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(&args[2]).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":rows,"guest_benchmark_commands":0,
        "runtime_changes":0,"performance_measurement":false})).unwrap();
}
