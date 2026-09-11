use super::*;
use crate::{Slot, VERSION, Limits};

#[path = "../../tests/common/call_copy_cases.rs"]
mod call_copy_cases;

fn function(frame: usize, align: usize, code: Vec<Op>) -> Function {
    Function { name: "native tree test".into(), frame_size: frame, frame_align: align,
        registers: 8, args: vec![], result: Slot { offset: 0, size: 8 }, code }
}
fn program(functions: Vec<Function>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions, data: vec![0; 16], statics: vec![], thread_locals: vec![] }
}
fn call(function: usize, args: Vec<Reg>, destination: Reg) -> Op { Op::Call { function, args, destination } }
fn local(dst: Reg, offset: usize) -> Op { Op::Local { dst, offset } }
fn imm(dst: Reg, value: u128) -> Op { Op::Imm { dst, value } }

// Native root Return copies onto its own result slot before truncation. This
// permits a direct-entry check with the same guest addresses as VM root entry;
// the harness reads the retained bytes only after generated execution returns.
fn check(p: &Program, profiled: bool) -> Result<(u128, TreeRun), String> {
    check_state(p, profiled).map(|(value, run, _, _)| (value, run))
}

fn check_state(p: &Program, profiled: bool) -> Result<(u128, TreeRun, Vec<u8>, Vec<u8>), String> {
    crate::validate(p).unwrap();
    let mut jit = Jit::new(p, profiled, MAX_CODE_BYTES).unwrap();
    // Exercise shared publication with ordinary regions both before and after
    // native dependencies. Older entries and fault identities remain valid.
    jit.ensure_function(p.entry).unwrap();
    let plan = jit.ensure_tree(p.entry)?.expect("test tree must be eligible");
    for id in 0..p.functions.len() { jit.ensure_function(id).unwrap(); }
    let f = &p.functions[p.entry];
    let bounds = plan.requirements(p.data.len(), 0, 0).unwrap();
    let base = bounds.root_base;
    let len = base + f.frame_size.max(1);
    let mut memory = vec![0xc7; bounds.memory_end + 32];
    memory[..p.data.len()].copy_from_slice(&p.data);
    memory[p.data.len()..len].fill(0);
    let mut heap = p.statics.clone();
    let mut registers = vec![u128::MAX; plan.register_slots];
    if crate::registers::needs_initial_zeroes(f) { registers[..f.registers].fill(0); }
    let mut hits: Vec<Vec<u64>> = p.functions.iter().map(|f| vec![0; f.code.len()]).collect();
    let table: Vec<_> = hits.iter_mut().map(|h| h.as_mut_ptr()).collect();
    let before = (memory.clone(), registers.clone(), heap.clone());
    for budget in [0, plan.instructions - 1] {
        let declined = unsafe { jit.run_tree(p.entry, budget, base + f.result.offset,
            table.as_ptr(), registers.as_mut_ptr(), base, memory.as_mut_ptr(), len,
            p.data.len(), heap.as_mut_ptr(), heap.len()) }?;
        assert!(declined.is_none());
        assert_eq!((&memory, &registers, &heap), (&before.0, &before.1, &before.2));
        assert!(hits.iter().flatten().all(|&n| n == 0));
    }
    let result = unsafe { jit.run_tree(p.entry, plan.instructions, base + f.result.offset,
        table.as_ptr(), registers.as_mut_ptr(), base, memory.as_mut_ptr(), len,
        p.data.len(), heap.as_mut_ptr(), heap.len()) };
    assert!(memory[bounds.memory_end..].iter().all(|&b| b == 0xc7), "prepared extent canary");
    let run = result?.unwrap();
    if profiled {
        let mut charged = 0;
        let mut calls = 0;
        for (id, row) in hits.iter().enumerate() {
            let entry = jit.trees.as_ref().unwrap().entries[id].as_ref();
            for (pc, &count) in row.iter().enumerate().filter(|(_, count)| **count != 0) {
                let end = entry.unwrap().ends[pc].unwrap();
                charged += count * (end - pc) as u64;
                calls += count * p.functions[id].code[pc..end].iter().filter(|op| matches!(op, Op::Call { .. })).count() as u64;
            }
        }
        assert_eq!(charged, run.instructions);
        assert_eq!(calls, run.calls);
    } else { assert!(hits.iter().flatten().all(|&n| n == 0)); }
    let mut value = [0; 16];
    value[..f.result.size].copy_from_slice(&memory[base + f.result.offset..base + f.result.offset + f.result.size]);
    Ok((u128::from_le_bytes(value), run, memory, heap))
}

fn differential(p: &Program) {
    let expected = crate::execute(p, &[], Limits::default());
    for profiled in [false, true] {
        match (&expected, check(p, profiled)) {
            (Ok(expected), Ok((value, run))) => {
                assert_eq!(value, expected.value);
                assert_eq!(run.instructions, expected.instructions);
                assert_eq!(run.peak_linear + p.statics.len(), expected.peak_memory);
            }
            (Err(expected), Err(actual)) => {
                if expected.contains("memory access") || expected.contains("read-only") || expected.contains("address overflow") {
                    assert_eq!(actual, "JIT guest memory access failed");
                } else { assert_eq!(&actual, expected); }
            }
            (expected, actual) => panic!("VM/native mismatch: {expected:?} / {actual:?}"),
        }
    }
}

#[test]
fn existing_call_copy_contracts_execute_as_complete_native_trees() {
    for case in call_copy_cases::cases() {
        let expected = crate::execute(&case.program, &[], Limits::default());
        assert_eq!(expected.as_ref().map(|r| r.value).map_err(String::as_str), case.expected, "{}", case.name);
        differential(&case.program);
    }
}

#[test]
fn nested_siblings_preserve_padding_caller_values_and_register_initialization() {
    for first in [1, 16, 64, 4096] {
        for second in [1, 16, 128] {
            let mut p = program(vec![
                function(17, 16, vec![local(0, 0), imm(1, 0x1234), Op::Store { address: 0, src: 1, size: 8 },
                    call(1, vec![0], 0), call(2, vec![0], 0), call(1, vec![0], 0), Op::Return]),
                function(17, first, vec![local(0, 0), call(3, vec![0], 0), Op::Return]),
                function(33, second, vec![local(0, 0), Op::Load { dst: 1, address: 0, size: 8 },
                    imm(2, 3), Op::Binary { dst: 1, overflow: 3, op: Binary::Add, a: 1, b: 2, bits: 64, signed: false },
                    Op::Store { address: 0, src: 1, size: 8 }, Op::Return]),
                function(31, 32, vec![Op::Assert { value: 7, expected: false, message: "reused register must be zero".into() },
                    local(0, 0), Op::Load { dst: 1, address: 0, size: 8 }, imm(2, 1),
                    Op::Binary { dst: 1, overflow: 3, op: Binary::Add, a: 1, b: 2, bits: 64, signed: false },
                    Op::Store { address: 0, src: 1, size: 8 }, imm(7, 987),
                    Op::Assert { value: 7, expected: true, message: "dirty reused register".into() }, Op::Return]),
            ]);
            for f in &mut p.functions[1..] { f.args = vec![Slot { offset: 0, size: 8 }]; }
            differential(&p);
            assert_eq!(check(&p, true).unwrap().0, 0x1239);
        }
    }
}

#[test]
fn all_copy_widths_and_overlapping_return_directions_match_vm() {
    for size in [0, 1, 3, 7, 8, 9, 15, 16, 17, 31, 32, 33, 63, 64, 65, 127, 128, 129, 257, 513] {
        for delta in [-7isize, 0, 1, 7] {
            let offset = 16usize;
            let destination = (offset as isize + delta) as usize;
            // Root frame at 1024, child at 2048; put return destination inside
            // child itself to exercise both overlapping memmove directions.
            let mut p = program(vec![function(1024, 16, vec![imm(0, 16),
                imm(1, (2048 + destination) as u128), call(1, vec![0], 1),
                local(2, 0), imm(3, (2048 + destination) as u128),
                // Child Return has truncated its frame: reading it must fail.
                Op::Load { dst: 4, address: 3, size: 1 }, Op::Store { address: 2, src: 4, size: 1 }, Op::Return]),
                function(1024, 16, vec![Op::Return])]);
            p.data = (0..1024).map(|n| ((n * 37 + 11) % 251) as u8).collect();
            p.functions[1].args = vec![Slot { offset, size }];
            p.functions[1].result = Slot { offset, size };
            differential(&p);
            // Observe retained bytes directly after a successful root return:
            // every destination byte must match a snapshot memmove, including
            // copies whose result destination is within their own callee frame.
            p.functions[0].code.truncate(3);
            p.functions[0].code.push(Op::Return);
            p.functions[0].result.size = 0;
            let mut expected = vec![0; 1024];
            expected[offset..offset + size].copy_from_slice(&p.data[16..16 + size]);
            expected.copy_within(offset..offset + size, destination);
            for profiled in [false, true] {
                let (_, _, memory, _) = check_state(&p, profiled).unwrap();
                assert_eq!(&memory[2048..3072], expected, "size={size}, delta={delta}");
            }
            p.functions[0].result.size = 8;
            // Now return to the caller, making copied bytes observable through
            // a rolling scalar checksum using ordinary bytecode operations.
            let root = &mut p.functions[0];
            root.code = vec![imm(0, 16), local(1, 0), call(1, vec![0], 1), imm(2, 0)];
            for byte in 0..size {
                root.code.extend([local(3, byte), Op::Load { dst: 4, address: 3, size: 1 },
                    Op::Binary { dst: 2, overflow: 5, op: Binary::Add, a: 2, b: 4, bits: 64, signed: false }]);
            }
            root.code.extend([local(3, 0), Op::Store { address: 3, src: 2, size: 8 }, Op::Return]);
            differential(&p);
        }
    }
}

#[test]
fn nested_faults_keep_original_identity_and_skip_parent_continuation() {
    for tail in [Op::Trap { message: "terminal cold path".into() },
        Op::Assert { value: 0, expected: true, message: "child assertion".into() },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Binary { dst: 1, overflow: 2, op: Binary::Div, a: 0, b: 0, bits: 64, signed: false }] {
        let p = program(vec![function(16, 16, vec![local(0, 0), call(1, vec![], 0),
                Op::Trap { message: "must not continue".into() }]),
            function(16, 32, vec![local(0, 0), call(2, vec![], 0), Op::Return]),
            function(16, 64, vec![tail, Op::Return])]);
        differential(&p);
    }
    // Untaken traps remain cold; one- and two-operation blocks are compiled.
    for value in [0, 1, 1u128 << 100] {
        let p = program(vec![function(16, 16, vec![imm(0, value),
            Op::Switch { value: 0, cases: vec![(1, 3), (1, 2), (1u128 << 100, 3)], otherwise: 2 },
            Op::Trap { message: "branch trap".into() }, Op::Return])]);
        differential(&p);
    }
}

#[test]
fn declining_code_capacity_never_publishes_a_partial_parent() {
    let p = program(vec![function(16, 16, vec![local(0, 0), call(1, vec![], 0), Op::Return]),
        function(16, 16, vec![Op::Return])]);
    for capacity in [0, 4, 64, 256, 1024, 65536] {
        let mut jit = Jit::new(&p, false, capacity).unwrap();
        let ready = jit.ensure_tree(0).unwrap();
        let state = jit.trees.as_ref().unwrap();
        if ready.is_some() { assert!(state.entries.iter().all(Option::is_some)); }
        assert!(jit.bytes <= capacity);
        let bytes = jit.bytes;
        let faults = jit.assertions.len();
        assert_eq!(jit.ensure_tree(0).unwrap(), ready);
        assert_eq!((jit.bytes, jit.assertions.len()), (bytes, faults));
    }
}

#[test]
fn return_to_heap_preserves_heap_arguments_and_all_copied_bytes() {
    for size in [0, 3, 16, 17, 31, 32, 33, 127, 128, 129, 513] {
        let mut p = program(vec![function(16, 16, vec![imm(0, crate::heap::TAG as u128 + 16),
                imm(1, crate::heap::TAG as u128 + 23), call(1, vec![0], 1), Op::Return]),
            function(1024, 16, vec![Op::Return])]);
        p.statics = (0..1024).map(|n| ((n * 41 + 17) % 251) as u8).collect();
        p.functions[1].args = vec![Slot { offset: 9, size }];
        p.functions[1].result = Slot { offset: 9, size };
        let mut expected = p.statics.clone();
        expected.copy_within(16..16 + size, 23);
        for profiled in [false, true] {
            let (_, _, _, heap) = check_state(&p, profiled).unwrap();
            assert_eq!(heap, expected, "size={size}");
        }
        differential(&p);
    }
}

#[test]
fn native_stack_and_callee_saved_registers_survive_maximum_depth_and_faults() {
    for depth in [1, 2, trees::MAX_DEPTH] {
        for fault in [false, true] {
            let functions = (0..depth).map(|id| function(16, 16, if id + 1 == depth {
                vec![if fault { Op::Trap { message: "deep trap".into() } } else { Op::Return }]
            } else { vec![local(0, 0), call(id + 1, vec![], 0), Op::Return] })).collect();
            let p = program(functions);
            for profiled in [false, true] {
                let mut jit = Jit::new(&p, profiled, MAX_CODE_BYTES).unwrap();
                let plan = jit.ensure_tree(0).unwrap().unwrap();
                let mut registers = vec![0u128; plan.register_slots];
                let mut memory = vec![0; 16 + plan.frame_span];
                let mut hits: Vec<Vec<u64>> = p.functions.iter().map(|f| vec![0; f.code.len()]).collect();
                let table: Vec<_> = hits.iter_mut().map(|h| h.as_mut_ptr()).collect();
                let mut cursor = TreeCursor { base: Cursor { remaining: plan.instructions, profile_hits: table[0] },
                    memory_len: 32, peak_linear: 32, return_address: 16, profile_table: table.as_ptr(), calls: 0, tree_instructions: 0, regions_ready: 0, stub_calls: 0 };
                let arguments = [registers.as_mut_ptr() as usize, 16, memory.as_mut_ptr() as usize, 32, 16,
                    0, 0, (&mut cursor as *mut TreeCursor) as usize];
                let entry = jit.trees.as_ref().unwrap().entries[0].as_ref().unwrap();
                let output = unsafe { jit.code.as_ref().unwrap().tree_abi_probe(entry.wrapper, arguments) };
                assert_eq!(output[0] as u64, if fault { ASSERTION_FAILURE_BASE } else { 0 });
                assert_eq!(&output[1..5], &[0x1357, 0x2468, 0x3579, 0x468a]);
                assert_eq!(output[5], output[6]);
                assert_eq!(output[6] % 16, 0);
                assert_eq!(cursor.calls, depth as u64 - 1);
                assert_eq!(cursor.memory_len, if fault { 16 + 16 * depth } else { 16 });
                assert_eq!(cursor.peak_linear, 16 + 16 * depth);
                if !fault { assert_eq!(cursor.base.remaining, 0); }
            }
        }
    }
}
