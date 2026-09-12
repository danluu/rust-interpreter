use crate::{Op, Program};

/// A true entry certifies that every direct-call source lies wholly within the
/// active caller frame. Analyze only a validated, immutable program. Facts stop
/// at basic-block boundaries; this does not infer pointer classes from values.
pub(crate) fn local_arguments(program: &Program) -> Vec<Vec<bool>> {
    program.functions.iter().map(|function| {
        let mut result = vec![false; function.code.len()];
        let mut starts = vec![false; function.code.len()];
        starts[0] = true;
        for (pc, op) in function.code.iter().enumerate() {
            match op {
                Op::Jump { target } => starts[*target] = true,
                Op::Switch { cases, otherwise, .. } => {
                    starts[*otherwise] = true;
                    for (_, target) in cases { starts[*target] = true; }
                }
                _ => {}
            }
            if matches!(op, Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. })
                && pc + 1 < starts.len()
            {
                starts[pc + 1] = true;
            }
        }
        // (definition epoch, Local offset). Epoch zero means unknown; every
        // block starts with a distinct nonzero epoch without clearing the table.
        let mut locals = vec![(0usize, 0usize); function.registers];
        let mut epoch = 1;
        for (pc, op) in function.code.iter().enumerate() {
            if starts[pc] { epoch = pc + 1; }
            if let Op::Call { function: callee, args, .. } = op {
                result[pc] = args.iter().zip(&program.functions[*callee].args).all(|(reg, slot)| {
                    let (defined, offset) = locals[*reg as usize];
                    defined == epoch && offset.checked_add(slot.size)
                        .is_some_and(|end| end <= function.frame_size)
                });
            }
            // Explicitly enumerate all writers so new opcodes require a review.
            // Copy destinations and call destinations are memory addresses, not
            // register writes; calls cannot access their caller's register arena.
            match op {
                Op::CallValue { destination, .. } => {
                    if let crate::CallDestination::Value(dst) = destination { locals[*dst as usize].0 = 0; }
                },
                Op::Local { dst, offset } => locals[*dst as usize] = (epoch, *offset),
                Op::Binary { dst, overflow, .. } => {
                    locals[*dst as usize].0 = 0;
                    locals[*overflow as usize].0 = 0;
                }
                Op::Imm { dst, .. } | Op::Load { dst, .. } | Op::Unary { dst, .. }
                | Op::Cast { dst, .. } | Op::Select { dst, .. } | Op::CompareBytes { dst, .. }
                | Op::Allocate { dst, .. } | Op::Reallocate { dst, .. } | Op::RandomBytes { dst, .. }
                | Op::CpuFeatureQuery { dst, .. }
                | Op::CAllocate { dst, .. } | Op::CReallocate { dst, .. } | Op::CAlignedAllocate { dst, .. }
                | Op::FloatBinary { dst, .. } | Op::FloatUnary { dst, .. } | Op::FloatConvert { dst, .. } => {
                    locals[*dst as usize].0 = 0;
                }
                Op::Store { .. } | Op::Copy { .. } | Op::CopyDynamic { .. }
                | Op::Jump { .. } | Op::Switch { .. } | Op::Assert { .. }
                | Op::Call { .. } | Op::CallIndirect { .. } | Op::Return | Op::Trap { .. }
                | Op::Deallocate { .. } | Op::CDeallocate { .. } | Op::RegisterTlsDestructor { .. } | Op::FillBytes { .. } | Op::ResetThreadLocals => {}
            }
        }
        result
    }).collect()
}

#[cfg(test)]
mod tests {
use super::local_arguments;
use crate::{Op, Program, Function, Slot, Binary, Unary, FloatBinary, FloatUnary, FloatConversion, VERSION};

fn call(args: Vec<u32>) -> Op {
    Op::Call { function: 1, args, destination: 3 }
}

fn plans(code: Vec<Op>, sizes: &[usize]) -> Vec<bool> {
    let p = Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![], statics: vec![], thread_locals: vec![],
        functions: vec![
            Function { name: "caller".into(), frame_size: 32, frame_align: 16,
                registers: 4, args: vec![], result: Slot { offset: 0, size: 0 }, code },
            Function { name: "callee".into(), frame_size: 64, frame_align: 16,
                registers: 0, args: sizes.iter().map(|size| Slot { offset: 0, size: *size }).collect(),
                result: Slot { offset: 0, size: 0 }, code: vec![Op::Return] },
        ],
    };
    crate::validate(&p).unwrap();
    local_arguments(&p).remove(0)
}

#[test]
fn local_extents_exact_end_zero_size_and_mixed_arguments() {
    for size in [0, 1, 8, 16, 32, 33] {
        for offset in [0, 1, 16, 24, 31, 32] {
            let marked = plans(vec![Op::Local { dst: 0, offset }, call(vec![0]), Op::Return], &[size]);
            assert_eq!(marked, [false, offset + size <= 32, false]);
        }
    }
    assert_eq!(plans(vec![call(vec![]), Op::Return], &[]), [true, false]);
    assert_eq!(plans(vec![Op::Local { dst: 0, offset: 0 }, call(vec![0, 1]), Op::Return], &[8, 8]), [false, false, false]);
    assert_eq!(plans(vec![Op::Local { dst: 0, offset: 0 }, Op::Local { dst: 1, offset: 24 }, call(vec![0, 1]), Op::Return], &[32, 8]), [false, false, true, false]);
    // A second Local replaces the old offset; zero-sized unknown pointers remain unproven.
    assert_eq!(plans(vec![Op::Local { dst: 0, offset: 0 }, Op::Local { dst: 0, offset: 32 }, call(vec![0]), Op::Return], &[8]), [false; 4]);
    assert_eq!(plans(vec![call(vec![0]), Op::Return], &[0]), [false; 2]);
}

#[test]
fn every_register_writer_invalidates_its_destination() {
    let writers = vec![
        Op::Imm { dst: 0, value: 0 }, Op::Load { dst: 0, address: 0, size: 8 },
        Op::Unary { dst: 0, op: Unary::Not, src: 0, bits: 64 },
        Op::Cast { dst: 0, src: 0, from: 64, to: 64, signed: false },
        Op::Select { dst: 0, condition: 0, yes: 0, no: 0 },
        Op::CompareBytes { dst: 0, left: 0, right: 0, size: 1 },
        Op::Allocate { dst: 0, size: 1, align: 1, zeroed: true },
        Op::Reallocate { dst: 0, pointer: 0, old_size: 1, align: 1, new_size: 1 },
        Op::RandomBytes { dst: 0, address: 0, size: 1 },
        Op::CpuFeatureQuery { dst: 0, name: 0, output: 1, output_len: 1, new_data: 1, new_len: 1 },
        Op::CAllocate { dst: 0, count: 1, size: 1, errno: 0, zeroed: true },
        Op::CReallocate { dst: 0, pointer: 0, size: 1, errno: 1 },
        Op::CAlignedAllocate { dst: 0, output: 0, align: 1, size: 1 },
        Op::FloatBinary { dst: 0, op: FloatBinary::Add, a: 0, b: 1, bits: 64 },
        Op::FloatUnary { dst: 0, op: FloatUnary::Neg, src: 0, bits: 64 },
        Op::FloatConvert { dst: 0, kind: FloatConversion::FloatToInt { signed: false }, src: 0, from: 64, to: 64 },
    ];
    for writer in writers {
        let label = format!("{writer:?}");
        assert_eq!(plans(vec![Op::Local { dst: 0, offset: 0 }, writer.clone(), call(vec![0]), Op::Return], &[8]), [false; 4], "{label}");
        assert!(plans(vec![Op::Local { dst: 0, offset: 0 }, writer, Op::Local { dst: 0, offset: 0 }, call(vec![0]), Op::Return], &[8])[3], "new Local after {label}");
    }
    for (dst, overflow) in [(0, 1), (1, 0), (0, 0)] {
        let writer = Op::Binary { dst, overflow, op: Binary::Add, a: 0, b: 1, bits: 64, signed: false };
        assert_eq!(plans(vec![Op::Local { dst: 0, offset: 0 }, writer, call(vec![0]), Op::Return], &[8]), [false; 4]);
    }
}

#[test]
fn facts_stop_at_joins_backedges_and_unreachable_blocks() {
    for code in [
        vec![Op::Jump { target: 2 }, Op::Local { dst: 0, offset: 0 }, call(vec![0]), Op::Return],
        vec![Op::Local { dst: 0, offset: 0 }, call(vec![0]), Op::Jump { target: 1 }, Op::Return],
        vec![Op::Local { dst: 0, offset: 0 }, Op::Switch { value: 1, cases: vec![(0, 3)], otherwise: 3 }, Op::Local { dst: 0, offset: 0 }, call(vec![0]), Op::Return],
        vec![Op::Local { dst: 0, offset: 0 }, Op::Return, call(vec![0]), Op::Return],
        vec![Op::Local { dst: 0, offset: 0 }, Op::Trap { message: "stop".into() }, call(vec![0]), Op::Return],
    ] {
        assert!(plans(code, &[8]).into_iter().all(|marked| !marked));
    }
    assert!(plans(vec![Op::Jump { target: 1 }, Op::Local { dst: 0, offset: 0 }, call(vec![0]), Op::Return], &[8])[2]);
}

#[test]
fn memory_destinations_and_calls_preserve_register_facts() {
    for op in [
        Op::Store { address: 0, src: 0, size: 8 },
        Op::Copy { dst: 0, src: 0, size: 8 },
        Op::CopyDynamic { dst: 0, src: 0, size: 1 },
        Op::FillBytes { address: 0, value: 1, size: 1 },
        Op::Deallocate { pointer: 0, size: 1, align: 1 },
        Op::CDeallocate { pointer: 0 },
        Op::Assert { value: 0, expected: true, message: "local".into() },
        Op::ResetThreadLocals,
        Op::Call { function: 1, args: vec![0], destination: 0 },
        Op::CallIndirect { callee: 1, args: vec![0], arg_sizes: vec![8], destination: 0, result_size: 0 },
    ] {
        let label = format!("{op:?}");
        let marked = plans(vec![Op::Local { dst: 0, offset: 0 }, op, call(vec![0]), Op::Return], &[8]);
        assert!(marked[2], "{label}");
    }
}

#[test]
fn indirect_calls_are_never_certified() {
    assert_eq!(plans(vec![Op::Local { dst: 0, offset: 0 }, Op::CallIndirect { callee: 1, args: vec![0], arg_sizes: vec![8], destination: 0, result_size: 0 }, Op::Return], &[8]), [false; 3]);
}

}
