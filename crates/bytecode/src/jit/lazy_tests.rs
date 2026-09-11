use super::*;
use crate::{Slot, VERSION};

fn fixture() -> Program {
    let functions = (0..3).map(|id| Function {
        name: format!("function_{id}"), frame_size: 16, frame_align: 16, registers: 2,
        args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![
            Op::Imm { dst: 0, value: u128::from(id == 0) },
            Op::Assert { value: 0, expected: true, message: format!("assertion_{id}") },
            Op::Imm { dst: 1, value: 9 }, Op::Return,
        ],
    }).collect();
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![], functions }
}
fn run(jit: &Jit<'_>, id: usize) -> Result<(usize, u64), String> {
    let mut registers = [0u128; 2];
    let mut memory = [0u8; 32];
    let mut hits = vec![0u64; jit.program.functions[id].code.len()];
    unsafe { jit.run(jit.blocks[id][0].unwrap(), hits.len(), 100_000,
        hits.as_mut_ptr(), registers.as_mut_ptr(), 16, memory.as_mut_ptr(), memory.len(),
        16, std::ptr::null_mut(), 0) }
}

#[test]
fn later_appends_keep_old_entries_and_assertion_identities_in_every_order() {
    let p = fixture(); crate::validate(&p).unwrap();
    for profiled in [false, true] {
        for order in [[2, 0, 1], [1, 2, 0], [0, 1, 2]] {
            let mut jit = Jit::new(&p, profiled, MAX_CODE_BYTES).unwrap();
            assert!(jit.code.is_none()); assert_eq!(jit.bytes, 0);
            for (index, id) in order.into_iter().enumerate() {
                let old: Vec<_> = jit.blocks.iter().map(|v| v.first().copied().flatten().map(|b| b.offset)).collect();
                assert!(jit.ensure_function(id).unwrap());
                let elapsed = jit.compile_nanos;
                assert!(!jit.ensure_function(id).unwrap());
                assert_eq!(jit.compile_nanos, elapsed);
                for previous in &order[..=index] {
                    if let Some(offset) = old[*previous] { assert_eq!(jit.blocks[*previous][0].unwrap().offset, offset); }
                    if *previous == 0 { assert_eq!(run(&jit, 0).unwrap(), (3, 3)); }
                    else { assert_eq!(run(&jit, *previous).unwrap_err(), format!("guest assertion: assertion_{previous} in function_{previous}")); }
                }
            }
            assert_eq!(jit.compiled_functions, 3); assert_eq!(jit.declined_functions, 0);
        }
    }
}

#[test]
fn declining_a_staged_function_preserves_code_budget_and_assertion_ids() {
    let mut p = fixture();
    p.functions[1].code.splice(2..2, (0..3000).map(|n| Op::Imm { dst: 1, value: n }));
    crate::validate(&p).unwrap();
    for profiled in [false, true] {
        let cold = Jit::new(&p, profiled, MAX_CODE_BYTES).unwrap();
        let a = cold.emit_function(&p.functions[0], MAX_CODE_BYTES / 4).unwrap().unwrap().words.len() * 4;
        let c = cold.emit_function(&p.functions[2], MAX_CODE_BYTES / 4).unwrap().unwrap().words.len() * 4;
        let mut jit = Jit::new(&p, profiled, a + c).unwrap();
        jit.ensure_function(0).unwrap();
        assert_eq!(jit.bytes, a);
        let offset = jit.blocks[0][0].unwrap().offset;
        let operations = jit.operations;
        jit.ensure_function(1).unwrap();
        assert_eq!(jit.bytes, a); assert_eq!(jit.operations, operations);
        assert!(jit.blocks[1].is_empty()); assert_eq!(jit.assertions.len(), 1);
        assert_eq!(jit.declined_functions, 1);
        assert!(!jit.ensure_function(1).unwrap());
        jit.ensure_function(2).unwrap();
        assert_eq!(jit.bytes, a + c); assert_eq!(jit.assertions.len(), 2);
        assert_eq!(jit.blocks[0][0].unwrap().offset, offset);
        assert_eq!(run(&jit, 0).unwrap(), (3, 3));
        assert_eq!(run(&jit, 2).unwrap_err(), "guest assertion: assertion_2 in function_2");
    }
}
