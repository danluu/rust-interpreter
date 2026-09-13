//! Saved-artifact diagnostic: never construct or execute JIT machine code.
pub use rust_interp_bytecode::*;
use serde_json::{Value,json};
use std::collections::{BTreeMap,BTreeSet};
#[path="../../../crates/bytecode/src/registers.rs"] mod registers;
#[path="../../../crates/bytecode/src/register_init.rs"] mod register_init;
mod proof;

fn number(v: &Value, key: &str) -> usize { usize::try_from(v[key].as_u64().unwrap()).unwrap() }
fn bounded_read(path: &std::ffi::OsStr, max: u64) -> Vec<u8> {
    assert!(std::fs::metadata(path).unwrap().len()<=max);
    let bytes=std::fs::read(path).unwrap();assert!(bytes.len() as u64<=max);bytes
}
fn main() {
    let args:Vec<_>=std::env::args_os().collect();assert_eq!(args.len(),4);
    let p:Program=bincode::deserialize(&bounded_read(&args[1],128*1024*1024)).unwrap();validate(&p).unwrap();
    let mapping:Value=serde_json::from_slice(&bounded_read(&args[2],256*1024*1024)).unwrap();
    assert_eq!(mapping["complete"],true);assert_eq!(mapping["reconstructed_bytes_match"],true);
    assert_eq!(mapping["profiled"],false);assert_eq!(mapping["resumable_calls"],true);
    let mut remaining=proof::MAX_GLOBAL_WORK;let mut seen=BTreeSet::new();let mut output=vec![];
    for saved in mapping["functions"].as_array().unwrap() {
        let id=number(saved,"function");assert!(seen.insert(id));let f=&p.functions[id];assert_eq!(saved["name"],f.name);
        let mut regions=BTreeMap::<usize,BTreeSet<usize>>::new();
        for span in saved["spans"].as_array().unwrap() {
            if let Some(pc)=span["pc"].as_u64() {
                let pc=usize::try_from(pc).unwrap();assert!(pc<f.code.len());
                let start=number(span,"region_pc");assert!(pc>=start);
                assert!(regions.entry(start).or_default().insert(pc));
            }
        }
        let mut reports=vec![];let mut last_end=0;
        for (start,pcs) in regions {
            let end=pcs.last().unwrap()+1;assert!(start>=last_end);last_end=end;
            assert!(pcs.iter().copied().eq(start..end));
            let report=proof::analyze(f,start,end,&mut remaining);
            reports.push(json!({"start":start,"end":end,"proof":report}));
        }
        output.push(json!({"function":id,"name":f.name,"frame_size":f.frame_size,"registers":f.registers,"regions":reports}));
    }
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(&args[3]).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":output,"global_work_remaining":remaining,
        "guest_commands":0,"runtime_changes":0,"performance_measurement":false})).unwrap();
}
