//! Typed feasibility metadata only; never execute the saved guest.
pub use rust_interp_bytecode::*;
use serde_json::json;
#[path="../../../crates/bytecode/src/registers.rs"] mod registers;
mod proof;

fn main() {
    let args:Vec<_>=std::env::args_os().collect();assert_eq!(args.len(),3);
    let bytes=std::fs::read(&args[1]).unwrap();assert!(bytes.len()<=128*1024*1024);
    let program:Program=bincode::deserialize(&bytes).unwrap();validate(&program).unwrap();
    assert!(program.functions.len()<=65536);
    let mut remaining=proof::MAX_GLOBAL_WORK;
    let rows:Vec<_>=program.functions.iter().enumerate().map(|(id,f)| {
        let plan=proof::memory_plan(&program,id,&mut remaining);
        json!({"function":id,"name":f.name,"frame_size":f.frame_size,"frame_align":f.frame_align,
            "registers":f.registers,"bytecode_operations":f.code.len(),"arguments":f.args,"result":f.result,"plan":plan})
    }).collect();
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(&args[2]).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":rows,"global_work_remaining":remaining,
        "guest_commands":0,"runtime_changes":0,"address_nonescape_proved":false})).unwrap();
}
