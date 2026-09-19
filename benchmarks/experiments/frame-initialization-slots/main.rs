//! Read validated saved bytecode and report proofs; never execute a guest.
pub use rust_interp_bytecode::*;
use serde_json::json;
#[path = "../../../crates/bytecode/src/registers.rs"]
mod registers;
#[path = "../../../crates/bytecode/src/register_init.rs"]
mod register_init;
#[path = "../../../crates/bytecode/src/jit/call_slots.rs"]
mod call_slots;
mod proof;
#[path = "../frame-initialization-constants/proof.rs"]
mod previous;

fn main() {
    let args: Vec<_> = std::env::args_os().collect(); assert_eq!(args.len(), 3);
    let input = std::fs::read(&args[1]).unwrap(); assert!(input.len() <= 128 * 1024 * 1024);
    let program: Program = bincode::deserialize(&input).unwrap(); validate(&program).unwrap();
    let old_effects = previous::effects(&program);
    let old_confined: Vec<_> = old_effects.iter().map(|p| p.eligible).collect();
    let mut old_remaining = previous::MAX_GLOBAL_WORK;
    let effects = proof::effects(&program);
    let confined: Vec<_> = effects.iter().map(|p| p.eligible).collect();
    let without = vec![false; confined.len()];
    let mut remaining = [proof::MAX_GLOBAL_WORK; 2];
    let rows: Vec<_> = program.functions.iter().enumerate().map(|(id, f)| {
        let old = previous::analyze_budgeted(&program,id,&old_confined,previous::Mode::Initialized,&mut old_remaining);
        let baseline = proof::analyze_budgeted(&program, id, &without, proof::Mode::Initialized, &mut remaining[0]);
        let enhanced = proof::analyze_budgeted(&program, id, &confined, proof::Mode::Initialized, &mut remaining[1]);
        let hints = call_slots::collect(f, &program);
        let calls: Vec<_> = f.code.iter().enumerate().filter_map(|(pc, op)| {
            let Op::Call { function, args, .. } = op else { return None; };
            let callee = &program.functions[*function];
            let offsets: Vec<_> = args.iter().enumerate().map(|(index, _)| hints.get(&pc).and_then(|h| h[index])).collect();
            let local = callee.args.iter().enumerate().all(|(index, slot)| slot.size == 0 || offsets[index]
                .and_then(|offset| offset.checked_add(slot.size)).is_some_and(|end| end <= f.frame_size));
            Some(json!({"pc":pc,"callee":function,"caller_local_arguments":local,"argument_hints":offsets}))
        }).collect();
        json!({"function":id,"name":f.name,"frame_size":f.frame_size,"frame_align":f.frame_align,
            "previous_confined":old_effects[id],"previous_initialization":old,
            "confined":effects[id],"cfg_without_callee_effects":baseline,"cfg_with_callee_effects":enhanced,"calls":calls})
    }).collect();
    let file = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[2]).unwrap();
    serde_json::to_writer(file, &json!({"status":"passed","functions":rows,"global_work_remaining":remaining,
        "previous_global_work_remaining":old_remaining,"caller_address_guards_required":true,"guest_commands":0,"runtime_changes":0})).unwrap();
}
