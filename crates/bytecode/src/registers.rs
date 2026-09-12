use crate::{Function, Op};

/// Registers have initial-zero semantics. Reused, initialized host storage can
/// retain its old values only when every read is preceded by a write in the
/// same basic block. This deliberately conservative proof needs no fixed point
/// or path assumptions. Calls cannot access their caller's register storage.
/// Call this only after program validation has checked registers and targets.
/// Fast block proof first; an entry-prefix fallback permits values carried
/// across blocks when their initial definitions dominate every continuation.
pub(crate) fn needs_initial_zeroes(function: &Function) -> bool {
    if !block_needs_initial_zeroes(function, &[]) {
        return false;
    }
    let mut entry = vec![false; function.registers];
    for op in &function.code {
        let mut needed = false;
        let mut written = [0; 2];
        let mut len = 0;
        visit_registers(
            op,
            |r| needed |= !entry[r as usize],
            |r| {
                written[len] = r;
                len += 1;
            },
        );
        // Outputs never excuse an earlier read, including aliased operands.
        if needed {
            return true;
        }
        for &r in &written[..len] {
            entry[r as usize] = true;
        }
        if matches!(
            op,
            Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }
        ) {
            break;
        }
    }
    block_needs_initial_zeroes(function, &entry)
}

// Keep the exporter's established inlining heuristic independent of the
// runtime initialization proof; this experiment changes register reuse only.
pub(crate) fn needs_initial_zeroes_for_inlining(function: &Function) -> bool {
    block_needs_initial_zeroes(function, &[])
}

fn block_needs_initial_zeroes(function: &Function, entry: &[bool]) -> bool {
    let mut starts = vec![false; function.code.len()];
    starts[0] = true;
    for (pc, op) in function.code.iter().enumerate() {
        match op {
            Op::Jump { target } => starts[*target] = true,
            Op::Switch {
                cases, otherwise, ..
            } => {
                starts[*otherwise] = true;
                for (_, target) in cases {
                    starts[*target] = true;
                }
            }
            _ => {}
        }
        if matches!(
            op,
            Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }
        ) && pc + 1 < starts.len()
        {
            starts[pc + 1] = true;
        }
    }
    // Epochs avoid clearing the definition table at every branch target.
    let mut defined = vec![0usize; function.registers];
    let mut epoch = 1;
    for (pc, op) in function.code.iter().enumerate() {
        if starts[pc] {
            epoch = pc + 1;
        }
        let mut needed = false;
        let mut read = |r: crate::Reg| {
            needed |=
                defined[r as usize] != epoch && !entry.get(r as usize).copied().unwrap_or(false)
        };
        // Collect outputs until all operands have been read: aliased outputs
        // cannot establish initialization for an earlier read in this opcode.
        let mut writes = [0; 2];
        let mut count = 0;
        visit_registers(op, &mut read, |r| {
            writes[count] = r;
            count += 1;
        });
        if needed {
            return true;
        }
        for &r in &writes[..count] {
            defined[r as usize] = epoch;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Binary, Slot};

    fn needs(code: Vec<Op>) -> bool {
        needs_initial_zeroes(&Function {
            name: "register-proof".into(),
            frame_size: 16,
            frame_align: 16,
            registers: 4,
            args: vec![],
            result: Slot {
                offset: 0,
                size: 16,
            },
            code,
        })
    }

    #[test]
    fn whole_register_writes_prove_straight_line_and_loop_reads() {
        assert!(!needs(vec![
            Op::Imm { dst: 0, value: 5 },
            Op::Binary {
                dst: 0,
                overflow: 1,
                op: Binary::Add,
                a: 0,
                b: 0,
                bits: 8,
                signed: false
            },
            Op::Assert {
                value: 1,
                expected: false,
                message: "overflow".into()
            },
            Op::Switch {
                value: 0,
                cases: vec![(10, 0)],
                otherwise: 4
            },
            Op::Return,
        ]));
    }

    #[test]
    fn skipped_definitions_and_aliased_outputs_need_initial_values() {
        assert!(needs(vec![
            Op::Jump { target: 2 },
            Op::Imm { dst: 0, value: 1 },
            Op::Assert {
                value: 0,
                expected: false,
                message: "skipped".into()
            },
            Op::Return,
        ]));
        // Its entry definition dominates the loop; no initial-zero read.
        assert!(!needs(vec![
            Op::Imm { dst: 0, value: 1 },
            Op::Switch {
                value: 0,
                cases: vec![(1, 1)],
                otherwise: 2
            },
            Op::Return,
        ]));
        assert!(needs(vec![
            Op::Binary {
                dst: 0,
                overflow: 1,
                op: Binary::Add,
                a: 0,
                b: 1,
                bits: 8,
                signed: false
            },
            Op::Return,
        ]));
    }

    #[test]
    fn calls_and_memory_destinations_are_reads() {
        for op in [
            Op::Call {
                function: 0,
                args: vec![],
                destination: 0,
            },
            Op::Call {
                function: 0,
                args: vec![1],
                destination: 0,
            },
            Op::CallIndirect {
                callee: 1,
                args: vec![],
                arg_sizes: vec![],
                destination: 0,
                result_size: 0,
            },
            Op::Copy {
                dst: 1,
                src: 0,
                size: 0,
            },
            Op::Load {
                dst: 1,
                address: 1,
                size: 0,
            },
        ] {
            assert!(needs(vec![op, Op::Return]));
        }
        assert!(!needs(vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Call {
                function: 0,
                args: vec![0],
                destination: 0
            },
            Op::Store {
                address: 0,
                src: 0,
                size: 0
            },
            Op::Return,
        ]));
    }
}

use crate::Reg;
/// Exhaustive operand access order: all reads, then complete-register writes.
/// Memory destinations and Call result addresses are register reads.
pub(crate) fn visit_registers(op: &Op, mut read: impl FnMut(Reg), mut write: impl FnMut(Reg)) {
    match op {
        Op::Imm { .. }
        | Op::Local { .. }
        | Op::Jump { .. }
        | Op::Return
        | Op::Trap { .. }
        | Op::ResetThreadLocals => {}
        Op::Load { address, .. } => read(*address),
        Op::Store { address, src, .. } => {
            read(*address);
            read(*src);
        }
        Op::Copy { dst, src, .. } => {
            read(*dst);
            read(*src);
        }
        Op::CopyDynamic { dst, src, size } => {
            read(*dst);
            read(*src);
            read(*size);
        }
        Op::Binary { a, b, .. } | Op::FloatBinary { a, b, .. } => {
            read(*a);
            read(*b);
        }
        Op::Unary { src, .. }
        | Op::Cast { src, .. }
        | Op::FloatUnary { src, .. }
        | Op::FloatConvert { src, .. } => read(*src),
        Op::Select {
            condition, yes, no, ..
        } => {
            read(*condition);
            read(*yes);
            read(*no);
        }
        Op::Switch { value, .. } | Op::Assert { value, .. } => read(*value),
        Op::Call {
            args, destination, ..
        } => {
            read(*destination);
            for &r in args {
                read(r);
            }
        }
        Op::CallValue {
            args, destination, ..
        } => {
            if let crate::CallDestination::Address(r) = destination {
                read(*r);
            }
            for arg in args {
                read(arg.register());
            }
        }
        Op::CallIndirect {
            callee,
            args,
            destination,
            ..
        } => {
            read(*callee);
            read(*destination);
            for &r in args {
                read(r);
            }
        }
        Op::CompareBytes {
            left, right, size, ..
        } => {
            read(*left);
            read(*right);
            read(*size);
        }
        Op::Allocate { size, align, .. } => {
            read(*size);
            read(*align);
        }
        Op::Deallocate {
            pointer,
            size,
            align,
        } => {
            read(*pointer);
            read(*size);
            read(*align);
        }
        Op::Reallocate {
            pointer,
            old_size,
            align,
            new_size,
            ..
        } => {
            read(*pointer);
            read(*old_size);
            read(*align);
            read(*new_size);
        }
        Op::FillBytes {
            address,
            value,
            size,
        } => {
            read(*address);
            read(*value);
            read(*size);
        }
        Op::RandomBytes { address, size, .. } => {
            read(*address);
            read(*size);
        }
        Op::CpuFeatureQuery {
            name,
            output,
            output_len,
            new_data,
            new_len,
            ..
        } => {
            for r in [name, output, output_len, new_data, new_len] {
                read(*r);
            }
        }
        Op::CAllocate {
            count, size, errno, ..
        } => {
            for r in [count, size, errno] {
                read(*r);
            }
        }
        Op::CDeallocate { pointer } => read(*pointer),
        Op::RegisterTlsDestructor { callback, argument } => {
            read(*callback);
            read(*argument);
        }
        Op::CReallocate {
            pointer,
            size,
            errno,
            ..
        } => {
            for r in [pointer, size, errno] {
                read(*r);
            }
        }
        Op::CAlignedAllocate {
            output,
            align,
            size,
            ..
        } => {
            for r in [output, align, size] {
                read(*r);
            }
        }
    }
    match op {
        Op::CallValue { destination, .. } => {
            if let crate::CallDestination::Value(r) = destination {
                write(*r);
            }
        }
        Op::Binary { dst, overflow, .. } => {
            write(*dst);
            write(*overflow);
        }
        Op::Imm { dst, .. }
        | Op::Local { dst, .. }
        | Op::Load { dst, .. }
        | Op::Unary { dst, .. }
        | Op::Cast { dst, .. }
        | Op::Select { dst, .. }
        | Op::CompareBytes { dst, .. }
        | Op::Allocate { dst, .. }
        | Op::Reallocate { dst, .. }
        | Op::RandomBytes { dst, .. }
        | Op::CpuFeatureQuery { dst, .. }
        | Op::CAllocate { dst, .. }
        | Op::CReallocate { dst, .. }
        | Op::CAlignedAllocate { dst, .. }
        | Op::FloatBinary { dst, .. }
        | Op::FloatUnary { dst, .. }
        | Op::FloatConvert { dst, .. } => write(*dst),
        Op::Store { .. }
        | Op::Copy { .. }
        | Op::CopyDynamic { .. }
        | Op::Jump { .. }
        | Op::Switch { .. }
        | Op::Assert { .. }
        | Op::Call { .. }
        | Op::CallIndirect { .. }
        | Op::Return
        | Op::Trap { .. }
        | Op::Deallocate { .. }
        | Op::CDeallocate { .. }
        | Op::RegisterTlsDestructor { .. }
        | Op::FillBytes { .. }
        | Op::ResetThreadLocals => {}
    }
}

#[cfg(test)]
#[path = "entry_register_zero_tests.rs"]
mod entry_register_zero_tests;

// A supplied argument and the explicitly initialized result register are valid
// on entry and every continuation. Retain the existing proof for other locals.
pub(crate) fn needs_initial_zeroes_with_inputs(function: &Function, inputs: &[crate::Reg]) -> bool {
    let mut entry = vec![false; function.registers];
    for &reg in inputs {
        entry[reg as usize] = true;
    }
    if !block_needs_initial_zeroes(function, &entry) {
        return false;
    }
    for op in &function.code {
        let mut needed = false;
        let mut written = [0; 2];
        let mut len = 0;
        visit_registers(
            op,
            |r| needed |= !entry[r as usize],
            |r| {
                written[len] = r;
                len += 1;
            },
        );
        if needed {
            return true;
        }
        for &r in &written[..len] {
            entry[r as usize] = true;
        }
        if matches!(
            op,
            Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }
        ) {
            break;
        }
    }
    block_needs_initial_zeroes(function, &entry)
}
