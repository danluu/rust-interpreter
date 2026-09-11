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
    for persistent in [false, true] { for stubs in [false, true] { for profiled in [false, true] {
        let config = || Limits { jit_persistent_registers: persistent, jit_native_call_stubs: stubs, ..limits(instructions, memory, frames, true) };
        let got = if profiled {
            execute_profiled(p, &[], config(), Engine::Jit).map(|(r, profile)| {
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
        } else { execute_with_engine(p, &[], config(), Engine::Jit) };
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
    } } }
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

#[test]
fn linked_call_stubs_remove_outer_vm_entries_and_keep_instruction_counts() {
    let p = fixture();
    let r = execute_with_engine(&p, &[], Limits { jit_native_calls: true, jit_native_call_stubs: true,
        ..Limits::default() }, Engine::Jit).unwrap();
    assert_eq!((r.value, r.instructions), (73, 18));
    assert_eq!(r.jit_tree_entries, 0);
    assert_eq!(r.jit_entries, 1);
    assert_eq!(r.jit_stub_calls, 2);
    assert_eq!(r.jit_tree_calls, 4);
    assert_eq!(r.jit_tree_instructions, 14);
    assert_eq!(r.jit_instructions, 16);
    assert_eq!(r.jit_call_stubs, 2);
    assert_eq!(execute_with_engine(&p, &[], Limits { jit_native_call_stubs: true, ..Limits::default() },
        Engine::Jit).unwrap_err(), "native Call stubs require native calls");
}

#[test]
fn native_call_stubs_link_ordinary_regions_across_loops_and_budget_declines() {
    let mut p = fixture();
    p.functions[0].code = vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 3 },
        Op::Imm { dst: 2, value: 1 }, Op::Call { function: 1, args: vec![], destination: 0 },
        Op::Binary { dst: 1, overflow: 3, op: Binary::Sub, a: 1, b: 2, bits: 64, signed: false },
        Op::Assert { value: 2, expected: true, message: "caller register survived".into() },
        Op::Switch { value: 1, cases: vec![(0, 7)], otherwise: 3 }, Op::Return];
    let r = execute_with_engine(&p, &[], Limits { jit_native_calls: true, jit_native_call_stubs: true,
        ..Limits::default() }, Engine::Jit).unwrap();
    assert_eq!((r.value, r.jit_entries, r.jit_stub_calls), (73, 1, 3));
    for instructions in 0..=r.instructions + 1 { same(&p, instructions, 65536, 10); }
    for frames in [1, 2, 3] { same(&p, 1000, 65536, frames); }
    // Untaken code still requires readiness, but cannot introduce a guest error.
    p.functions[2].frame_align = 1 << 20;
    p.functions[0].code = vec![Op::Imm { dst: 0, value: 0 },
        Op::Switch { value: 0, cases: vec![(0, 3)], otherwise: 2 },
        Op::Call { function: 1, args: vec![], destination: 0 }, Op::Return];
    same(&p, 1000, 4096, 2);
}

#[test]
fn heap_growth_rechecks_live_limits_before_reusing_a_ready_region() {
    let mut p = fixture();
    p.functions[0].code = vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 32 },
        Op::Imm { dst: 2, value: 16 }, Op::Call { function: 1, args: vec![], destination: 0 },
        Op::Allocate { dst: 3, size: 1, align: 2, zeroed: true },
        Op::Call { function: 1, args: vec![], destination: 0 },
        Op::Deallocate { pointer: 3, size: 1, align: 2 },
        Op::Call { function: 1, args: vec![], destination: 0 }, Op::Return];
    for memory in [352, 353, 399, 400, 401, 433, 480, 481, 4096] { same(&p, 1000, memory, 10); }
    let steps = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap().instructions;
    for budget in 0..=steps { same(&p, budget, 401, 10); }
}

#[test]
fn a_vm_callee_with_larger_alignment_invalidates_prepared_region_extent() {
    let mut p = fixture();
    p.functions.push(function(16, 4096, vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 0 },
        Op::CopyDynamic { dst: 0, src: 0, size: 1 }, Op::Return]));
    p.functions[0].code = vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 0 },
        Op::Imm { dst: 2, value: 0 }, Op::Call { function: 1, args: vec![], destination: 0 },
        Op::Call { function: 3, args: vec![], destination: 0 },
        Op::Call { function: 1, args: vec![], destination: 0 }, Op::Return];
    for memory in [4096, 4200, 4448, 4449, 8192, 65536] { same(&p, 1000, memory, 10); }
    let steps = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap().instructions;
    for budget in 0..=steps { same(&p, budget, 65536, 10); }
}
