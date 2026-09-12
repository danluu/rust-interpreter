use super::*;
use crate::{Binary, Program, VERSION};

fn function(code: Vec<Op>) -> Function {
    Function { name: "frame-proof".into(), frame_size: 16, frame_align: 8, registers: 4,
        args: vec![], result: Slot { offset: 0, size: 0 }, code }
}

fn check(f: &Function) -> Proof {
    let p = Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions: vec![f.clone()], data: vec![], statics: vec![], thread_locals: vec![] };
    crate::validate(&p).unwrap();
    analyze(f)
}

fn local(dst: Reg, offset: usize) -> Op { Op::Local { dst, offset } }
fn store(address: Reg, size: u8) -> Op { Op::Store { address, src: 3, size } }
fn load(address: Reg, size: u8) -> Op { Op::Load { dst: 3, address, size } }

#[test]
fn every_partial_extent_and_return_padding_is_checked() {
    for written in 0..=16 {
        for read in 0..=16 {
            let mut f = function(vec![local(0, 0), store(0, written), load(0, read), Op::Return]);
            assert_eq!(check(&f).eligible, read <= written, "write {written}, read {read}");
            f.code.remove(2);
            f.result = Slot { offset: 0, size: read as usize };
            assert_eq!(check(&f).eligible, read <= written, "return {read}, write {written}");
        }
    }
}

#[test]
fn arguments_seed_only_their_exact_bytes() {
    let mut f = function(vec![local(0, 4), load(0, 8), Op::Return]);
    f.args = vec![Slot { offset: 4, size: 8 }];
    assert!(check(&f).eligible);
    f.code[0] = local(0, 3);
    assert_eq!(check(&f).decline.unwrap().reason, "local_read_before_write");
    f.code[0] = local(0, 5);
    assert!(!check(&f).eligible);
}

#[test]
fn unknown_alias_reads_need_the_whole_frame_initialized() {
    for size in 0..=16 {
        let f = function(vec![local(0, 0), store(0, size), load(1, 1), Op::Return]);
        assert_eq!(check(&f).eligible, size == 16);
    }
    assert!(check(&function(vec![load(1, 0), Op::Return])).eligible);
    assert!(!check(&function(vec![store(1, 16), local(0, 0), load(0, 1), Op::Return])).eligible);
}

#[test]
fn copy_reads_before_writing_with_overlap_and_aliased_registers() {
    assert!(!check(&function(vec![local(0, 0), Op::Copy { dst: 0, src: 0, size: 8 }, Op::Return])).eligible);
    let mut f = function(vec![local(0, 0), local(1, 4), store(0, 8),
        Op::Copy { dst: 1, src: 0, size: 8 }, load(1, 8), Op::Return]);
    assert!(check(&f).eligible);
    f.code[3] = Op::Copy { dst: 0, src: 1, size: 8 };
    assert!(!check(&f).eligible);
    f.code = vec![local(0, 0), store(0, 8), Op::Load { dst: 0, address: 0, size: 8 }, load(0, 8), Op::Return];
    assert_eq!(check(&f).decline.unwrap().reason, "unknown_pointer_read");
}

#[test]
fn both_binary_outputs_invalidate_pointer_facts() {
    for (dst, overflow) in [(0, 1), (1, 0), (0, 0)] {
        let f = function(vec![local(0, 0), store(0, 8),
            Op::Binary { dst, overflow, op: Binary::Add, a: 2, b: 3, bits: 64, signed: false },
            load(0, 8), Op::Return]);
        assert_eq!(check(&f).decline.unwrap().reason, "unknown_pointer_read");
    }
}

#[test]
fn blocks_do_not_borrow_facts_from_skipped_or_prior_iterations() {
    for code in [
        vec![Op::Jump { target: 3 }, local(0, 0), store(0, 16), local(0, 0), load(0, 1), Op::Return],
        vec![local(0, 0), store(0, 16), Op::Jump { target: 3 }, local(0, 0), load(0, 1), Op::Return],
        vec![local(0, 0), store(0, 16), load(0, 1), Op::Switch { value: 2, cases: vec![(0, 2)], otherwise: 4 }, Op::Return],
        vec![Op::Return, local(0, 0), load(0, 1), Op::Return],
    ] { assert!(!check(&function(code)).eligible); }
    let f = function(vec![local(0, 0), store(0, 16), load(0, 1),
        Op::Switch { value: 2, cases: vec![(0, 0)], otherwise: 4 }, Op::Return]);
    assert!(check(&f).eligible);
}

#[test]
fn dynamic_effects_need_full_initialization() {
    for effect in [Op::CopyDynamic { dst: 0, src: 1, size: 2 },
        Op::CompareBytes { dst: 0, left: 1, right: 2, size: 3 },
        Op::FillBytes { address: 0, value: 1, size: 2 }, Op::ResetThreadLocals,
        Op::Call { function: 0, args: vec![], destination: 0 }]
    {
        assert!(!check(&function(vec![effect.clone(), Op::Return])).eligible);
        assert!(check(&function(vec![local(0, 0), store(0, 16), effect, Op::Return])).eligible);
    }
}

#[test]
fn zero_sized_frames_still_have_one_live_byte() {
    let mut f = function(vec![local(0, 0), load(0, 1), Op::Return]);
    f.frame_size = 0;
    assert!(!check(&f).eligible);
    f.code.insert(1, store(0, 1));
    assert!(check(&f).eligible);
    f.code = vec![Op::Return];
    assert!(check(&f).eligible);
}

#[test]
fn out_of_frame_local_access_is_not_a_proof() {
    let f = function(vec![local(0, 16), store(0, 1), Op::Return]);
    assert_eq!(check(&f).decline.unwrap().reason, "write_outside_frame");
    let f = function(vec![local(0, 16), load(0, 1), Op::Return]);
    assert_eq!(check(&f).decline.unwrap().reason, "read_outside_frame");
}

#[test]
fn bounds_decline_without_an_unbounded_analysis() {
    let mut f = function(vec![Op::Return]);
    for (size, regs, ops) in [(MAX_FRAME + 1, 4, 1), (16, MAX_REGISTERS + 1, 1), (16, 4, MAX_OPS + 1)] {
        f.frame_size = size; f.registers = regs; f.code = vec![Op::Return; ops];
        assert_eq!(check(&f).decline.unwrap().reason, "size_limit");
    }
    f.frame_size = MAX_FRAME; f.registers = MAX_REGISTERS; f.code = vec![Op::Return; 100];
    let p = check(&f);
    assert_eq!(p.decline.unwrap().reason, "work_limit");
    assert!(p.work <= MAX_WORK + MAX_FRAME + MAX_REGISTERS);
}

#[test]
fn a_callee_proof_does_not_prove_argument_sources() {
    let mut callee = function(vec![local(0, 0), store(0, 16), Op::Return]);
    callee.args = vec![Slot { offset: 0, size: 8 }];
    assert!(check(&callee).eligible);
    let caller = function(vec![local(0, 16), Op::Call { function: 1, args: vec![0], destination: 1 }, Op::Return]);
    let p = Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions: vec![caller, callee], data: vec![], statics: vec![], thread_locals: vec![] };
    crate::validate(&p).unwrap();
    assert!(!crate::calls::local_arguments(&p)[0][1]);
}

#[test]
fn accepted_programs_match_an_independent_path_and_byte_mask_oracle() {
    // Explicit byte masks are independent of the proof's address and range
    // routines. Explore every branch and loop state, including return reads.
    // Registers 0/1 hold the two byte addresses; 3 is an unknown pointer.
    let choices = vec![
        (Op::Store { address: 0, src: 2, size: 1 }, 0, 1),
        (Op::Store { address: 1, src: 2, size: 1 }, 0, 2),
        (Op::Load { dst: 2, address: 0, size: 1 }, 1, 0),
        (Op::Load { dst: 2, address: 1, size: 1 }, 2, 0),
        (Op::Load { dst: 2, address: 3, size: 1 }, 3, 0),
        (Op::Copy { dst: 1, src: 0, size: 1 }, 1, 2),
        (Op::Copy { dst: 0, src: 1, size: 1 }, 2, 1),
        (Op::Jump { target: 2 }, 0, 0),
        (Op::Jump { target: 6 }, 0, 0),
        (Op::Switch { value: 2, cases: vec![(0, 3)], otherwise: 6 }, 0, 0),
        (Op::Return, 1, 0),
    ];
    let mut accepted = 0;
    for seed in [0u8, 2] {
        for mut shape in 0..choices.len().pow(4) {
            let mut ops = vec![local(0, 0), local(1, 1)];
            let mut masks = vec![(0, 0), (0, 0)];
            for _ in 0..4 {
                let (op, read, write) = &choices[shape % choices.len()];
                shape /= choices.len(); ops.push(op.clone()); masks.push((*read, *write));
            }
            ops.push(Op::Return); masks.push((1, 0));
            let mut f = function(ops);
            f.frame_size = 2;
            f.result = Slot { offset: 0, size: 1 };
            if seed != 0 { f.args.push(Slot { offset: 1, size: 1 }); }
            if !check(&f).eligible { continue; }
            accepted += 1;
            let mut visited = std::collections::BTreeSet::new();
            let mut todo = vec![(0usize, seed)];
            while let Some((pc, bytes)) = todo.pop() {
                if !visited.insert((pc, bytes)) { continue; }
                let (read, write) = masks[pc];
                assert_eq!(read & !bytes, 0, "pc {pc}, bytes {bytes}, {:?}", f.code);
                let next = bytes | write;
                match &f.code[pc] {
                    Op::Jump { target } => todo.push((*target, next)),
                    Op::Switch { cases, otherwise, .. } => {
                        todo.push((*otherwise, next));
                        for (_, target) in cases { todo.push((*target, next)); }
                    }
                    Op::Return => {},
                    _ => todo.push((pc + 1, next)),
                }
            }
        }
    }
    assert!(accepted > 100);
}
