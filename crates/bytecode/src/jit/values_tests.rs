use super::*;
use crate::Slot;

fn function(code: Vec<Op>, registers: usize) -> Function {
    Function { name: "liveness".into(), frame_size: 16, frame_align: 16, registers,
        args: vec![], result: Slot { offset: 0, size: 0 }, code }
}

#[test]
fn operand_visitation_preserves_aliases_and_memory_address_reads() {
    let events = std::cell::RefCell::new(vec![]);
    crate::registers::visit_registers(&Op::Binary { dst: 0, overflow: 1, op: Binary::Add,
        a: 0, b: 1, bits: 128, signed: false },
        |r| events.borrow_mut().push(('r', r)), |r| events.borrow_mut().push(('w', r)));
    assert_eq!(events.into_inner(), [('r', 0), ('r', 1), ('w', 0), ('w', 1)]);
    let p = function(vec![Op::CallIndirect { callee: 0, args: vec![1], arg_sizes: vec![8],
        destination: 2, result_size: 8 }, Op::CopyDynamic { dst: 3, src: 4, size: 5 }, Op::Return], 6);
    let a = analyze(&p).unwrap();
    for r in 0..6 { assert!(a.live.at(0, r)); }
    for r in 0..6 { assert_eq!(a.live.after(0, r), r >= 3); }
    for r in 0..6 { assert!(!a.live.at(2, r)); }
}

#[test]
fn liveness_keeps_loop_inputs_but_discards_overwritten_and_terminal_values() {
    let p = function(vec![
        Op::Imm { dst: 0, value: 1 },
        Op::Binary { dst: 1, overflow: 2, op: Binary::Add, a: 1, b: 0, bits: 128, signed: false },
        Op::Switch { value: 2, cases: vec![(0, 1)], otherwise: 3 },
        Op::Imm { dst: 1, value: 0 }, Op::Assert { value: 1, expected: false, message: "zero".into() },
        Op::Return, Op::Assert { value: 3, expected: true, message: "unreachable".into() }, Op::Return,
    ], 4);
    let a = analyze(&p).unwrap();
    assert!(a.live.at(0, 1));
    assert!(!a.live.at(0, 0));
    assert!(a.live.at(1, 0) && a.live.at(1, 1));
    assert!(!a.live.at(1, 2)); // produced before the branch
    assert!(!a.live.at(3, 1)); // overwritten before its next read
    assert!(!a.live.at(5, 3)); // unreachable tail does not cross Return
    assert!(a.live.at(6, 3));
    assert!(a.registers.contains(&1));
    assert!(a.registers.len() <= 3);
}

#[test]
fn bounded_liveness_matches_independent_path_search_on_seeded_graphs() {
    let mut seed = 0x856f_251du64;
    for _ in 0..200 {
        let mut next = |bound: usize| { seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17; seed as usize % bound };
        let n = 8 + next(20);
        let mut code = vec![];
        let mut inputs = vec![];
        let mut outputs = vec![];
        let mut edges = vec![];
        for pc in 0..n {
            let (a, b, c) = (next(8) as Reg, next(8) as Reg, next(8) as Reg);
            let target = next(n);
            let (op, reads, writes, successors) = match if pc == n - 1 { 5 } else { next(6) } {
                0 => (Op::Imm { dst: a, value: 1 }, vec![], vec![a], vec![pc + 1]),
                1 => (Op::Binary { dst: a, overflow: b, op: Binary::Sub, a: b, b: c, bits: 128, signed: false }, vec![b, c], vec![a, b], vec![pc + 1]),
                2 => (Op::Store { address: a, src: b, size: 8 }, vec![a, b], vec![], vec![pc + 1]),
                3 => (Op::Switch { value: a, cases: vec![(0, target)], otherwise: pc + 1 }, vec![a], vec![], vec![target, pc + 1]),
                4 => (Op::Jump { target }, vec![], vec![], vec![target]),
                _ => (Op::Return, vec![], vec![], vec![]),
            };
            code.push(op); inputs.push(reads); outputs.push(writes); edges.push(successors);
        }
        let a = analyze(&function(code, 8)).unwrap();
        for start in 0..n { for reg in 0..8 {
            // Search every path until its first read/write of this value,
            // independently of the worklist/set transfer implementation.
            let mut stack = vec![start];
            let mut visited = vec![false; n];
            let mut expected = false;
            while let Some(pc) = stack.pop() {
                if visited[pc] { continue; }
                visited[pc] = true;
                if inputs[pc].contains(&reg) { expected = true; break; }
                if !outputs[pc].contains(&reg) { stack.extend(&edges[pc]); }
            }
            assert_eq!(a.live.at(start, reg), expected, "start={start} reg={reg}");
        } }
    }
}

#[test]
fn analysis_limits_decline_without_a_partial_assignment() {
    let p = function(vec![Op::Imm { dst: 0, value: 1 }, Op::Return], 1);
    assert!(analyze_with_work(&p, 0).is_none());
    assert!(analyze(&function(vec![Op::Return], MAX_REGISTERS + 1)).is_none());
    assert!(analyze(&function(vec![Op::Return; MAX_PCS + 1], 0)).is_none());
    assert!(analyze(&function(vec![Op::Return; 1025], MAX_REGISTERS)).is_none());
    assert!(analyze(&function(vec![Op::Return], 0)).unwrap().registers.is_empty());
    let a = analyze(&function(vec![Op::Assert { value: 2050, expected: false, message: "far".into() }, Op::Return], 2051)).unwrap();
    assert!(a.live.at(0, 2050));
    assert!(!a.live.at(1, 2050));
}

#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
#[test]
fn persistent_pairs_preserve_the_host_abi_through_nested_stubs_and_faults() {
    use crate::{Program, VERSION};
    use crate::jit::native_calls::TreeCursor;
    for depth in [1, 2, trees::MAX_DEPTH] { for fault in ["none", "trap", "assert", "argument", "result", "after"] {
        let mut functions = vec![];
        for id in 0..=depth {
            let mut code = vec![Op::Imm { dst: 1, value: 1 << 127 }, Op::Imm { dst: 2, value: 3 },
                Op::Local { dst: 0, offset: 0 }, Op::Jump { target: 4 },
                Op::Assert { value: 1, expected: true, message: "wide input".into() },
                Op::Assert { value: 2, expected: true, message: "counter".into() },
                Op::Assert { value: 0, expected: true, message: "frame pointer".into() }];
            code.push(if id < depth {
                Op::Call { function: id + 1,
                    args: if id == 0 && fault == "argument" { vec![3] } else { vec![] },
                    destination: if id == 0 && fault == "result" { 3 } else { 0 } }
            } else { match fault {
                "trap" => Op::Trap { message: "deep trap".into() },
                "assert" => Op::Assert { value: 3, expected: true, message: "deep assertion".into() },
                _ => Op::Imm { dst: 3, value: 0 },
            } });
            for _ in 0..2 { for r in [1, 2, 0] {
                code.push(Op::Assert { value: r, expected: true, message: "caller value".into() });
            } }
            code.push(Op::Return);
            if id == 0 && fault == "after" { code[8] = Op::Load { dst: 3, address: 3, size: 8 }; }
            let mut f = function(code, 4);
            f.result.size = 8;
            if id == 1 && fault == "argument" { f.args = vec![Slot { offset: 8, size: 8 }]; }
            assert_eq!(analyze(&f).unwrap().registers.len(), 3);
            functions.push(f);
        }
        let p = Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
            functions, data: vec![0;16], statics: vec![], thread_locals: vec![] };
        crate::validate(&p).unwrap();
        for profiled in [false, true] {
            let mut jit = Jit::new_with_options(&p, profiled, MAX_CODE_BYTES, true, true).unwrap();
            jit.ensure_function(0).unwrap();
            assert_eq!(jit.register_pairs, 3 * (depth + 1));
            let plan = jit.ready_tree(1).unwrap().0;
            let (end, register_end, _) = jit.region_plans[0].requirements(32, 4).unwrap();
            for ready in [false, true] { for budget in [0, 3, 4, 7, plan.instructions + 8, plan.instructions + 32] { for pc in [0, 7, 8] {
                let mut memory = vec![0;end+32]; memory[end..].fill(0xad);
                let mut registers = vec![0u128;register_end];
                registers[..3].copy_from_slice(&[16, 1<<127, 3]);
                let mut hits: Vec<Vec<u64>> = p.functions.iter().map(|f| vec![0;f.code.len()]).collect();
                let table: Vec<_> = hits.iter_mut().map(|h| h.as_mut_ptr()).collect();
                let mut ordinary = vec![0;p.functions[0].code.len()];
                let mut cursor = TreeCursor { base: Cursor { remaining: budget, profile_hits: ordinary.as_mut_ptr() },
                    memory_len: 32, peak_linear: 32, return_address: 0, profile_table: table.as_ptr(),
                    calls: 0, tree_instructions: 0, regions_ready: u64::from(ready), stub_calls: 0 };
                let arguments = [registers.as_mut_ptr() as usize, 16, memory.as_mut_ptr() as usize, 32, 16,
                    0, 0, std::ptr::addr_of_mut!(cursor) as usize];
                let output = unsafe { jit.code.as_ref().unwrap().tree_abi_probe(jit.blocks[0][pc].unwrap().offset, arguments) };
                assert_eq!(&output[1..5], &[0x1357, 0x2468, 0x3579, 0x468a]);
                assert_eq!(&output[7..], &[0x579b, 0x68ac, 0x79bd, 0x8ace, 0x9bdf, 0xace0]);
                assert_eq!(output[5], output[6]); assert_eq!(output[6] % 16, 0);
                assert!(cursor.base.remaining <= budget);
                assert!(cursor.peak_linear <= end);
                assert!(memory[end..].iter().all(|&b| b == 0xad));
                if output[0] as u64 >= FAILURE_MIN { assert_ne!(fault, "none"); }
                else {
                    // A budget of four finishes the entry block and declines
                    // the next block at PC 4 before consuming its instructions.
                    assert!([0,4,7,8,14].contains(&output[0]),
                        "depth={depth} fault={fault} ready={ready} budget={budget} pc={pc} output={output:?}");
                }
                if ready && pc == 0 && budget == plan.instructions + 32 {
                    assert_eq!(output[0] as u64 >= FAILURE_MIN, fault != "none");
                }
                if !ready { assert_eq!((cursor.calls, cursor.stub_calls), (0, 0)); }
            } } }
        }
    } }
}
