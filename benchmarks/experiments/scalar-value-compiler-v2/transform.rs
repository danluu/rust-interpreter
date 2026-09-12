//! Final bytecode proof for typed, private MIR storage. Not a generic optimizer.
use rust_interp_bytecode::{
    CallArgument as A, CallDestination as D, Function, Op, Program, Reg, Slot,
    diagnostic_visit_registers as registers,
    scalar_abi::{Artifact, FunctionAbi},
};
use std::collections::BTreeMap;

pub(super) const MAX_LOCALS: usize = 4096;
pub(super) const MAX_FUNCTIONS: usize = 10_000;
const MAX_CANDIDATES: usize = 256;
const MAX_OPERATIONS: usize = 100_000;
const MAX_REGISTERS: usize = 100_000;
const MAX_WORK: usize = 32_000_000;

pub(crate) struct Binding {
    pub function: usize,
    pub name: String,
    pub slots: Vec<Slot>,
    pub eligible: Vec<bool>,
    pub arguments: Vec<Option<usize>>,
}
#[derive(Default, Debug, serde::Serialize)]
pub(super) struct Report {
    functions: usize,
    slots: usize,
    argument_registers: usize,
    result_registers: usize,
    private_registers: usize,
    value_calls: usize,
    value_arguments: usize,
    value_destinations: usize,
    removed_addresses: usize,
    rewritten_accesses: usize,
    removed_moves: usize,
    declined_functions: usize,
    candidate_slots: usize,
    rejected_uses: usize,
    proof_work: usize,
}
fn width(size: usize) -> bool {
    matches!(size, 1 | 2 | 4 | 8 | 16)
}
fn same(a: Slot, b: Slot) -> bool {
    a.offset == b.offset && a.size == b.size
}
fn starts(code: &[Op]) -> Vec<bool> {
    let mut out = vec![false; code.len()];
    out[0] = true;
    for (pc, op) in code.iter().enumerate() {
        match op {
            Op::Jump { target } => out[*target] = true,
            Op::Switch {
                cases, otherwise, ..
            } => {
                out[*otherwise] = true;
                for (_, target) in cases {
                    out[*target] = true;
                }
            }
            _ => {}
        }
        if matches!(
            op,
            Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }
        ) && pc + 1 < out.len()
        {
            out[pc + 1] = true;
        }
    }
    out
}
fn fail(message: &str) -> Result<(), String> {
    Err(message.into())
}

pub(super) fn apply(
    mut program: Program,
    bindings: Vec<Binding>,
) -> Result<(Artifact, Report), String> {
    rust_interp_bytecode::validate(&program)?;
    if program.version != rust_interp_bytecode::VERSION {
        return Err("scalar compiler requires strict bytecode".into());
    }
    if program.functions.len() > MAX_FUNCTIONS {
        return Err("scalar compiler function bound exceeded".into());
    }
    let signatures: Vec<_> = program
        .functions
        .iter()
        .map(|f| {
            (
                f.args.iter().map(|s| s.size).collect::<Vec<_>>(),
                f.result.size,
            )
        })
        .collect();
    let mut abi: Vec<_> = program
        .functions
        .iter()
        .map(|f| FunctionAbi {
            arguments: vec![None; f.args.len()],
            result: None,
        })
        .collect();
    let mut report = Report::default();
    let mut seen = vec![false; program.functions.len()];
    for binding in bindings {
        let id = binding.function;
        if id >= seen.len() || std::mem::replace(&mut seen[id], true) {
            return Err("invalid scalar compiler function identity".into());
        }
        promote(
            &mut program.functions[id],
            &signatures,
            &binding,
            &mut abi[id],
            &mut report,
        )?;
    }
    Ok((Artifact::scalar(program, abi)?, report))
}

fn promote(
    f: &mut Function,
    signatures: &[(Vec<usize>, usize)],
    b: &Binding,
    abi: &mut FunctionAbi,
    report: &mut Report,
) -> Result<(), String> {
    if f.name != b.name
        || b.slots.len() != b.eligible.len()
        || b.arguments.len() != f.args.len()
        || b.slots.is_empty()
        || !same(f.result, b.slots[0])
    {
        return fail("scalar compiler slot identity changed");
    }
    for (slot, local) in f.args.iter().zip(&b.arguments) {
        if let Some(local) = local {
            if b.slots.get(*local).is_none_or(|s| !same(*s, *slot)) {
                return fail("scalar compiler argument binding changed");
            }
        }
    }
    for s in &b.slots {
        if s.offset
            .checked_add(s.size)
            .is_none_or(|end| end > f.frame_size)
        {
            return fail("scalar compiler local extent changed");
        }
    }
    let mut work = f
        .code
        .len()
        .checked_mul(3)
        .and_then(|n| n.checked_add(f.registers));
    // The per-operand Call proof below may inspect the whole argument list.
    // Charge that worst case before doing any analysis or mutation.
    for op in &f.code {
        if let Op::Call { args, .. } = op {
            work = work.and_then(|n| {
                args.len()
                    .checked_add(1)?
                    .checked_mul(args.len() + 1)?
                    .checked_add(n)
            });
        }
    }
    if b.slots.len() > MAX_LOCALS
        || f.code.len() > MAX_OPERATIONS
        || f.registers > MAX_REGISTERS
        || work
            .and_then(|n| n.checked_add(report.proof_work))
            .is_none_or(|n| n > MAX_WORK)
    {
        report.declined_functions += 1;
        return Ok(());
    }
    report.proof_work += work.unwrap();
    // Every colored owner must be eligible. Partial overlaps reject both sides.
    let mut groups = BTreeMap::<(usize, usize), bool>::new();
    for (slot, yes) in b.slots.iter().zip(&b.eligible) {
        if slot.size != 0 {
            *groups.entry((slot.offset, slot.size)).or_insert(true) &= *yes && width(slot.size);
        }
    }
    let groups: Vec<_> = groups.into_iter().collect();
    let mut slots = vec![];
    let mut previous = 0;
    for (i, &((offset, size), yes)) in groups.iter().enumerate() {
        let end = offset + size;
        if yes && previous <= offset && groups.get(i + 1).is_none_or(|&((next, _), _)| next >= end)
        {
            slots.push(Slot { offset, size });
        }
        previous = previous.max(end);
    }
    if slots.len() > MAX_CANDIDATES {
        report.declined_functions += 1;
        return Ok(());
    }
    if slots.is_empty() {
        return Ok(());
    }
    report.candidate_slots += slots.len();
    let offsets: BTreeMap<_, _> = slots
        .iter()
        .enumerate()
        .map(|(i, s)| (s.offset, i))
        .collect();
    let mut writers = vec![0usize; f.registers];
    let mut addresses = vec![None; f.registers];
    for op in &f.code {
        registers(op, |_| {}, |r| writers[r as usize] += 1);
        if let Op::Local { dst, offset } = op {
            addresses[*dst as usize] = offsets.get(offset).copied();
        }
    }
    let mut admitted = vec![true; slots.len()];
    let mut used = vec![0usize; slots.len()];
    for op in &f.code {
        if let Op::Local { dst, offset } = op {
            if let Some((&start, &i)) = offsets.range(..=offset).next_back() {
                // Check every definition, including earlier definitions of a
                // reused address register and addresses into a candidate interior.
                if *offset < start + slots[i].size
                    && (*offset != start || writers[*dst as usize] != 1)
                {
                    admitted[i] = false;
                }
            }
        }
    }
    let blocks = starts(&f.code);
    let mut definitions = vec![0usize; f.registers];
    let mut epoch = 0;
    for (pc, op) in f.code.iter().enumerate() {
        if blocks[pc] {
            epoch = pc + 1;
        }
        registers(
            op,
            |r| {
                if let Some(i) = addresses[r as usize] {
                    let size = slots[i].size;
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
                        Op::Call {
                            function,
                            args,
                            destination,
                        } => {
                            let (sizes, result) = &signatures[*function];
                            let mut seen = false;
                            let mut valid = true;
                            if *destination == r {
                                seen = true;
                                valid &= *result == size;
                            }
                            for (&arg, &n) in args.iter().zip(sizes) {
                                if arg == r {
                                    seen = true;
                                    valid &= n == size;
                                }
                            }
                            seen && valid
                        }
                        _ => false,
                    };
                    if !allowed || definitions[r as usize] != epoch {
                        admitted[i] = false;
                    }
                    used[i] += 1;
                }
            },
            |_| {},
        );
        if let Op::Local { dst, .. } = op {
            definitions[*dst as usize] = epoch;
        }
    }
    for (yes, count) in admitted.iter_mut().zip(used) {
        *yes &= count > 0;
    }
    report.rejected_uses += admitted.iter().filter(|&&yes| !yes).count();
    let mut canonical = vec![None; slots.len()];
    for (i, &yes) in admitted.iter().enumerate() {
        if yes {
            canonical[i] = Some(f.registers as Reg);
            f.registers += 1;
        }
    }
    if canonical.iter().all(Option::is_none) {
        return Ok(());
    }
    let by_slot = |slot: Slot| {
        offsets
            .get(&slot.offset)
            .copied()
            .filter(|&i| same(slots[i], slot))
            .and_then(|i| canonical[i])
    };
    for (out, local) in abi.arguments.iter_mut().zip(&b.arguments) {
        if let Some(i) = local {
            *out = by_slot(b.slots[*i]);
        }
    }
    abi.result = by_slot(f.result);
    let input: std::collections::BTreeSet<_> = abi.arguments.iter().filter_map(|r| *r).collect();
    if input.len() != abi.arguments.iter().filter(|r| r.is_some()).count() {
        return fail("scalar compiler aliased formal registers");
    }
    let mut code = Vec::with_capacity(f.code.len() + slots.len());
    for r in canonical.iter().filter_map(|r| *r) {
        if !input.contains(&r) && abi.result != Some(r) {
            code.push(Op::Imm { dst: r, value: 0 });
            report.private_registers += 1;
        }
    }
    let promoted = |r: Reg| addresses[r as usize].and_then(|i| canonical[i]);
    let mov = |dst, src, size: usize| Op::Cast {
        dst,
        src,
        from: (size * 8) as u8,
        to: (size * 8) as u8,
        signed: false,
    };
    let mut mapped = vec![0; f.code.len()];
    for (pc, op) in f.code.iter().enumerate() {
        mapped[pc] = code.len();
        match op {
            Op::Local { dst, .. } if promoted(*dst).is_some() && pc + 1 < f.code.len() => {
                report.removed_addresses += 1;
            }
            Op::Load { dst, address, size } if promoted(*address).is_some() => {
                code.push(mov(*dst, promoted(*address).unwrap(), *size as usize));
                report.rewritten_accesses += 1;
            }
            Op::Store { address, src, size } if promoted(*address).is_some() => {
                code.push(mov(promoted(*address).unwrap(), *src, *size as usize));
                report.rewritten_accesses += 1;
            }
            Op::Copy { dst, src, size } if promoted(*dst).is_some() || promoted(*src).is_some() => {
                code.push(match (promoted(*dst), promoted(*src)) {
                    (Some(dst), Some(src)) => mov(dst, src, *size),
                    (Some(dst), None) => Op::Load {
                        dst,
                        address: *src,
                        size: *size as u8,
                    },
                    (None, Some(src)) => Op::Store {
                        address: *dst,
                        src,
                        size: *size as u8,
                    },
                    _ => unreachable!(),
                });
                report.rewritten_accesses += 1;
            }
            Op::Call {
                function,
                args,
                destination,
            } if promoted(*destination).is_some()
                || args.iter().any(|r| promoted(*r).is_some()) =>
            {
                let args = args
                    .iter()
                    .map(|r| match promoted(*r) {
                        Some(r) => {
                            report.value_arguments += 1;
                            A::Value(r)
                        }
                        None => A::Address(*r),
                    })
                    .collect();
                let destination = match promoted(*destination) {
                    Some(r) => {
                        report.value_destinations += 1;
                        D::Value(r)
                    }
                    None => D::Address(*destination),
                };
                code.push(Op::CallValue {
                    function: *function,
                    args,
                    destination,
                });
                report.value_calls += 1;
            }
            _ => code.push(op.clone()),
        }
    }
    for op in &mut code {
        match op {
            Op::Jump { target } => *target = mapped[*target],
            Op::Switch {
                cases, otherwise, ..
            } => {
                for (_, target) in cases {
                    *target = mapped[*target];
                }
                *otherwise = mapped[*otherwise];
            }
            _ => {}
        }
    }
    f.code = code;
    // Canonical ABI outputs have known widths, so this existing pass cannot
    // classify their final writes as removable temporary captures.
    let scalars: Vec<_> = canonical
        .iter()
        .enumerate()
        .filter_map(|(i, r)| r.map(|r| (r, (slots[i].size * 8) as u8)))
        .collect();
    report.removed_moves += scalar_moves::eliminate(&mut f.code, f.registers as u32, &scalars);
    report.functions += 1;
    report.slots += canonical.iter().filter(|r| r.is_some()).count();
    report.argument_registers += abi.arguments.iter().filter(|r| r.is_some()).count();
    report.result_registers += usize::from(abi.result.is_some());
    Ok(())
}

#[cfg(test)]
#[path = "scalar_value_transform_tests.rs"]
mod tests;

#[path = "scalar_promote_moves.rs"]
mod scalar_moves;
