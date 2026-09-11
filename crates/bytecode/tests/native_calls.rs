#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{Binary, Engine, Function, Limits, Op, Program, Slot, VERSION,
    execute_with_engine, execute_profiled, FUNCTION_POINTER_TAG, HEAP_POINTER_TAG};
#[path = "common/call_copy_cases.rs"]
mod cases;

fn limits(instructions: u64, memory: usize, frames: usize, native: bool) -> Limits {
    Limits { instructions, memory, frames, jit_native_calls: native, ..Limits::default() }
}
fn same(p: &Program, instructions: u64, memory: usize, frames: usize) {
    let reference = execute_with_engine(p, &[], limits(instructions, memory, frames, false), Engine::Interpreter);
    for profiled in [false, true] {
        let got = if profiled {
            execute_profiled(p, &[], limits(instructions, memory, frames, true), Engine::Jit).map(|(r, profile)| {
                let mut charged = 0;
                let mut trees = 0;
                for f in &profile.functions {
                    charged += f.interpreted.iter().sum::<u64>();
                    for (pc, count) in f.jit_blocks.iter().enumerate().filter(|(_, n)| **n != 0) {
                        charged += count * (f.jit_block_ends[pc] - pc) as u64;
                    }
                    for (pc, count) in f.jit_tree_blocks.iter().enumerate().filter(|(_, n)| **n != 0) {
                        trees += count * (f.jit_tree_block_ends[pc] - pc) as u64;
                    }
                }
                assert_eq!(charged + trees, r.instructions);
                assert_eq!(trees, r.jit_tree_instructions);
                r
            })
        } else { execute_with_engine(p, &[], limits(instructions, memory, frames, true), Engine::Jit) };
        match (&reference, got) {
            (Ok(want), Ok(got)) => {
                assert_eq!((got.value, got.instructions, got.peak_memory), (want.value, want.instructions, want.peak_memory));
                assert!(got.jit_tree_instructions <= got.jit_instructions);
                assert!(got.jit_tree_entries <= got.jit_entries);
                assert!(got.jit_tree_bytes <= got.jit_bytes);
            }
            (Err(want), Err(got)) => {
                if got == "JIT guest memory access failed" {
                    assert!(want.contains("memory access") || want.contains("read-only") || want.contains("address overflow"), "{want}");
                } else { assert_eq!(&got, want, "instructions={instructions} memory={memory} frames={frames}"); }
            }
            (want, got) => panic!("instructions={instructions} memory={memory} frames={frames}: {want:?} / {got:?}"),
        }
    }
}
fn function(frame_size: usize, frame_align: usize, code: Vec<Op>) -> Function {
    Function { name: "native transition".into(), frame_size, frame_align, registers: 4,
        args: vec![], result: Slot { offset: 0, size: 8 }, code }
}
fn fixture() -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![], functions: vec![
            function(16, 16, vec![Op::Local { dst: 0, offset: 0 },
                Op::Call { function: 1, args: vec![], destination: 0 },
                Op::Call { function: 1, args: vec![], destination: 0 }, Op::Return]),
            function(17, 64, vec![Op::Local { dst: 0, offset: 0 },
                Op::Call { function: 2, args: vec![], destination: 0 }, Op::Return]),
            function(33, 128, vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 73 },
                Op::Store { address: 0, src: 1, size: 8 }, Op::Return]),
        ] }
}

#[test]
fn real_vm_transition_removes_nested_dispatch_and_counts_profiles_exactly() {
    let p = fixture();
    same(&p, 1000, 4096, 10);
    let r = execute_with_engine(&p, &[], limits(1000, 4096, 10, true), Engine::Jit).unwrap();
    assert_eq!(r.value, 73);
    assert_eq!(r.jit_tree_entries, 2);
    assert_eq!(r.jit_tree_calls, 2);
    assert_eq!(r.jit_tree_instructions, 14);
    assert_eq!(r.jit_tree_compiled_functions, 2);
    assert!(r.jit_tree_bytes > 0);
    let off = execute_with_engine(&p, &[], Limits::default(), Engine::Jit).unwrap();
    assert_eq!((off.jit_tree_bytes, off.jit_tree_entries), (0, 0));
    assert_eq!(execute_with_engine(&p, &[], limits(100, 4096, 10, true), Engine::Interpreter).unwrap_err(),
        "native calls require the JIT engine");
}

#[test]
fn every_budget_boundary_and_tight_live_limits_keep_vm_behavior() {
    let p = fixture();
    for instructions in 0..=20 { same(&p, instructions, 4096, 10); }
    for frames in 0..=4 { for memory in [0, 16, 31, 95, 128, 256, 352, 353, 512, 4096] {
        same(&p, 1000, memory, frames);
    } }
    // Conservative whole-tree bounds can exceed the actual peak. The old VM
    // path still succeeds at the exact working-memory boundary.
    for memory in 336..=368 { same(&p, 1000, memory, 3); }
    for capacity in [0, 4, 64, 256] {
        let r = execute_with_engine(&p, &[], Limits { jit_code_bytes: capacity, jit_native_calls: true,
            ..Limits::default() }, Engine::Jit).unwrap();
        assert_eq!(r.value, 73);
        assert!(r.jit_bytes <= capacity);
    }
}

#[test]
fn existing_arguments_aliases_and_fault_order_survive_the_vm_hook() {
    for case in cases::cases() {
        let reference = execute_with_engine(&case.program, &[], Limits::default(), Engine::Interpreter);
        assert_eq!(reference.as_ref().map(|r| r.value).map_err(String::as_str), case.expected, "{}", case.name);
        let steps = reference.map(|r| r.instructions).unwrap_or(20);
        for instructions in 0..=steps + 1 { same(&case.program, instructions, 65536, 10); }
        for frames in [1, 2, 3] { same(&case.program, 1000, 65536, frames); }
    }
    let mut p = fixture();
    p.functions[2].args = vec![Slot { offset: 0, size: 8 }];
    p.functions[1].code = vec![Op::Imm { dst: 0, value: u128::MAX },
        Op::Call { function: 2, args: vec![0], destination: 0 }, Op::Return];
    for memory in [200, 350, 1000, 65536] { for frames in [1, 2, 3, 10] { same(&p, 1000, memory, frames); } }
}

#[test]
fn cold_branches_and_recursion_use_conservative_preentry_declines() {
    let mut p = fixture();
    p.functions[1].code = vec![Op::Imm { dst: 0, value: 0 },
        Op::Switch { value: 0, cases: vec![(0, 4)], otherwise: 2 },
        Op::Call { function: 2, args: vec![], destination: 0 },
        Op::Trap { message: "untaken".into() }, Op::Return];
    for frames in [2, 3] { for instructions in 0..=14 { same(&p, instructions, 4096, frames); } }
    // A recursion cycle is unavailable as a tree. Depth errors remain guest
    // errors in the VM, without recursive host preparation.
    p.functions[1].code = vec![Op::Call { function: 1, args: vec![], destination: 0 }, Op::Return];
    for frames in [1, 2, 4, 64] { same(&p, 1000, 65536, frames); }
}

#[test]
fn tls_callback_nested_calls_finish_through_the_original_vm_teardown() {
    let mut p = fixture();
    p.statics = vec![0; 32];
    p.functions[0].code = vec![Op::Imm { dst: 0, value: (FUNCTION_POINTER_TAG | 2) as u128 },
        Op::Imm { dst: 1, value: 0 }, Op::RegisterTlsDestructor { callback: 0, argument: 1 },
        Op::ResetThreadLocals, Op::Imm { dst: 0, value: (HEAP_POINTER_TAG + 16) as u128 },
        Op::Local { dst: 1, offset: 0 }, Op::Copy { src: 0, dst: 1, size: 8 }, Op::Return];
    p.functions[1].args = vec![Slot { offset: 0, size: 8 }];
    p.functions[1].result.size = 0;
    p.functions[1].code = vec![Op::Local { dst: 0, offset: 0 },
        Op::Call { function: 2, args: vec![], destination: 0 }, Op::Return];
    p.functions[2].code = vec![Op::Imm { dst: 0, value: (HEAP_POINTER_TAG + 16) as u128 },
        Op::Load { dst: 1, address: 0, size: 8 }, Op::Imm { dst: 2, value: 73 },
        Op::Binary { dst: 1, overflow: 3, op: Binary::Add, a: 1, b: 2, bits: 64, signed: false },
        Op::Store { address: 0, src: 1, size: 8 }, Op::Return];
    let steps = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap().instructions;
    for instructions in 0..=steps { same(&p, instructions, 65536, 10); }
    for frames in [1, 2, 3] { same(&p, 1000, 65536, frames); }
    assert_eq!(execute_with_engine(&p, &[], limits(1000, 65536, 10, true), Engine::Jit).unwrap().value, 73);
    p.functions[2].code = vec![Op::Trap { message: "native callback child failed".into() }];
    same(&p, 1000, 65536, 10);
}

#[test]
fn c_allocations_enable_heap_access_in_native_returns_and_regular_regions() {
    let p = Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![], functions: vec![
            function(16, 16, vec![Op::Imm { dst: 1, value: 8 }, Op::Imm { dst: 2, value: 1 },
                Op::Local { dst: 3, offset: 8 }, Op::CAllocate { dst: 0, count: 2, size: 1, errno: 3, zeroed: true },
                Op::Local { dst: 1, offset: 0 }, Op::Imm { dst: 2, value: 73 },
                Op::Store { address: 1, src: 2, size: 8 },
                Op::Call { function: 1, args: vec![1], destination: 0 },
                Op::Load { dst: 2, address: 0, size: 8 }, Op::Store { address: 1, src: 2, size: 8 },
                Op::Assert { value: 2, expected: true, message: "heap value".into() }, Op::Return]),
            Function { args: vec![Slot { offset: 0, size: 8 }], ..function(16, 16, vec![Op::Return]) },
        ] };
    same(&p, 1000, 65536, 10);
    for native in [false, true] {
        assert_eq!(execute_with_engine(&p, &[], limits(1000, 65536, 10, native), Engine::Jit).unwrap().value, 73);
    }
}
