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
