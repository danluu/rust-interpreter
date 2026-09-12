//! Only for private, non-address-exposed primitive MIR slots. The caller must
//! prove that other pointers cannot alias these ranges. This is not a general
//! optimizer for externally supplied bytecode.
use rust_interp_bytecode::{Op, Reg, Slot};
use std::collections::BTreeMap;

#[derive(Default, Debug)]
pub(super) struct Report {
    pub slots: usize,
    pub removed_addresses: usize,
    pub rewritten: usize,
    pub removed_moves: usize,
}

// Explicit matches force review when the bytecode gains a register operand.
fn registers(op: &Op, read: impl FnMut(Reg), write: impl FnMut(Reg)) {
    rust_interp_bytecode::diagnostic_visit_registers(op, read, write);
}

fn starts(code: &[Op]) -> Vec<bool> {
    let mut start = vec![false; code.len()];
    start[0] = true;
    for (pc, op) in code.iter().enumerate() {
        match op {
            Op::Jump { target } => start[*target] = true,
            Op::Switch {
                cases, otherwise, ..
            } => {
                start[*otherwise] = true;
                for (_, target) in cases {
                    start[*target] = true;
                }
            }
            _ => {}
        }
        if matches!(
            op,
            Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }
        ) && pc + 1 < start.len()
        {
            start[pc + 1] = true;
        }
    }
    start
}

pub(super) fn promote(code: &mut Vec<Op>, count: &mut u32, slots: &[Slot]) -> Report {
    if slots.is_empty()
        || slots.len() > 256
        || code.is_empty()
        || code.len() > 100_000
        || *count > 100_000
    {
        return Report::default();
    }
    let by_offset: BTreeMap<_, _> = slots
        .iter()
        .enumerate()
        .map(|(i, s)| (s.offset, i))
        .collect();
    assert_eq!(slots.len(), by_offset.len());
    for slot in slots {
        assert!([1, 2, 4, 8, 16].contains(&slot.size));
    }
    let mut writer_counts = vec![0u32; *count as usize];
    let mut addresses = vec![None; *count as usize];
    let mut candidate = vec![true; slots.len()];
    let mut uses = vec![0usize; slots.len()];
    for op in code.iter() {
        registers(op, |_| {}, |r| writer_counts[r as usize] += 1);
        if let Op::Local { dst, offset } = op {
            if let Some(&slot) = by_offset.get(offset) {
                addresses[*dst as usize] = Some(slot);
            }
        }
    }
    for (r, &slot) in addresses.iter().enumerate() {
        if let Some(slot) = slot {
            if writer_counts[r] != 1 {
                candidate[slot] = false;
            }
        }
    }
    let start = starts(code);
    let mut defined = vec![0usize; *count as usize];
    let mut epoch = 0;
    for (pc, op) in code.iter().enumerate() {
        if start[pc] {
            epoch = pc + 1;
        }
        registers(
            op,
            |r| {
                if let Some(slot) = addresses[r as usize] {
                    let size = slots[slot].size;
                    let allowed = match op {
                        Op::Load {
                            address, size: n, ..
                        } => *address == r && usize::from(*n) == size,
                        Op::Store {
                            address,
                            src,
                            size: n,
                        } => *address == r && *src != r && usize::from(*n) == size,
                        Op::Copy { src, dst, size: n } => (*src == r || *dst == r) && *n == size,
                        _ => false,
                    };
                    if !allowed || defined[r as usize] != epoch {
                        candidate[slot] = false;
                    }
                    uses[slot] += 1;
                }
            },
            |_| {},
        );
        if let Op::Local { dst, .. } = op {
            defined[*dst as usize] = epoch;
        }
    }
    for (yes, uses) in candidate.iter_mut().zip(uses) {
        *yes &= uses > 0;
    }
    let mut canonical = vec![None; slots.len()];
    let mut output = Vec::with_capacity(code.len() + slots.len());
    let mut report = Report::default();
    for (slot, &yes) in candidate.iter().enumerate() {
        if yes {
            let dst = *count;
            *count += 1;
            canonical[slot] = Some(dst);
            output.push(Op::Imm { dst, value: 0 });
            report.slots += 1;
        }
    }
    if report.slots == 0 {
        return report;
    }
    let promoted = |r: Reg| addresses[r as usize].and_then(|slot| canonical[slot]);
    let mov = |dst, src, size: usize| Op::Cast {
        dst,
        src,
        from: (size * 8) as u8,
        to: (size * 8) as u8,
        signed: false,
    };
    let mut mapped = vec![0usize; code.len()];
    for (pc, op) in code.iter().enumerate() {
        mapped[pc] = output.len();
        match op {
            Op::Local { dst, .. } if promoted(*dst).is_some() => {
                report.removed_addresses += 1;
            }
            Op::Load { dst, address, size } if promoted(*address).is_some() => {
                output.push(mov(*dst, promoted(*address).unwrap(), *size as usize));
                report.rewritten += 1;
            }
            Op::Store { address, src, size } if promoted(*address).is_some() => {
                output.push(mov(promoted(*address).unwrap(), *src, *size as usize));
                report.rewritten += 1;
            }
            Op::Copy { dst, src, size } if promoted(*dst).is_some() || promoted(*src).is_some() => {
                match (promoted(*dst), promoted(*src)) {
                    (Some(dst), Some(src)) => output.push(mov(dst, src, *size)),
                    (Some(dst), None) => output.push(Op::Load {
                        dst,
                        address: *src,
                        size: *size as u8,
                    }),
                    (None, Some(src)) => output.push(Op::Store {
                        address: *dst,
                        src,
                        size: *size as u8,
                    }),
                    _ => unreachable!(),
                }
                report.rewritten += 1;
            }
            _ => output.push(op.clone()),
        }
    }
    for op in &mut output {
        match op {
            Op::Jump { target } => *target = mapped[*target],
            Op::Switch {
                cases, otherwise, ..
            } => {
                *otherwise = mapped[*otherwise];
                for (_, target) in cases {
                    *target = mapped[*target];
                }
            }
            _ => {}
        }
    }
    *code = output;
    let scalars: Vec<_> = canonical
        .iter()
        .enumerate()
        .filter_map(|(i, r)| r.map(|r| (r, (slots[i].size * 8) as u8)))
        .collect();
    report.removed_moves = scalar_moves::eliminate(code, *count, &scalars);
    report
}

#[cfg(test)]
#[path = "scalar_promote_tests.rs"]
mod tests;

#[path = "scalar_promote_moves.rs"]
mod scalar_moves;
