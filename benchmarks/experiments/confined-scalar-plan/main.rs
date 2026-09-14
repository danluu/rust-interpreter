//! Typed feasibility metadata only; never execute the saved guest.
pub use rust_interp_bytecode::*;
use serde_json::json;
#[path="../../../crates/bytecode/src/registers.rs"] mod registers;
#[path="../../../crates/bytecode/src/register_init.rs"] mod register_init;
mod proof;
mod scalar_ir;

fn main() {
    let args:Vec<_>=std::env::args_os().collect();assert_eq!(args.len(),3);
    let bytes=std::fs::read(&args[1]).unwrap();assert!(bytes.len()<=128*1024*1024);
    let program:Program=bincode::deserialize(&bytes).unwrap();validate(&program).unwrap();
    assert!(program.functions.len()<=65536);
    let mut remaining=proof::MAX_GLOBAL_WORK;
    let mut scalar_remaining=128_000_000usize;
    let rows:Vec<_>=program.functions.iter().enumerate().map(|(id,f)| {
        let plan=proof::memory_plan(&program,id,&mut remaining);
        let limit=250_000usize.min(scalar_remaining);
        let scalar=scalar_ir::lower(f,&plan,limit);
        scalar_remaining=scalar_remaining.saturating_sub(match &scalar {
            Ok(p)=>p.work,Err("no_memory_plan")=>0,Err(_)=>limit,
        });
        let native=scalar.as_ref().ok().map(|p| [false,true].map(|profiled| {
            match scalar_ir::native_leaf::emit(p,profiled) {
                Ok(code)=>json!({"profiled":profiled,"eligible":true,"code_bytes":code.words.len()*4,"stack_bytes":code.stack_bytes}),
                Err(reason)=>json!({"profiled":profiled,"eligible":false,"decline":reason}),
            }
        }));
        json!({"function":id,"name":f.name,"frame_size":f.frame_size,"frame_align":f.frame_align,
            "registers":f.registers,"bytecode_operations":f.code.len(),"arguments":f.args,"result":f.result,"plan":plan,
            "scalar":scalar_ir::summary(&scalar),"native":native})
    }).collect();
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(&args[2]).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":rows,"global_work_remaining":remaining,
        "guest_commands":0,"runtime_changes":0,"address_nonescape_proved":false,"scalar_work_remaining":scalar_remaining})).unwrap();
}
