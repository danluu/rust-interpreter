//! Bounded advisory caller-frame offsets. Runtime equality guards remain required.
use crate::{Binary, Function, Op, Program};
use std::collections::BTreeMap;

const MAX_REGISTERS: usize = 65_536;
const MAX_OPS: usize = 500_000;
const MAX_WORK: usize = 4_000_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Fact { Local(usize), Imm(u128) }

fn transfer(op: &Op, facts: &mut [Option<Fact>], frame_size: usize) {
    let mut outputs = vec![];
    match *op {
        Op::Local { dst, offset } => outputs.push((dst, Fact::Local(offset))),
        Op::Imm { dst, value } => outputs.push((dst, Fact::Imm(value))),
        Op::Binary { dst, overflow, op: Binary::Add, a, b, bits: 64, signed: false } => {
            let pair = match (facts[a as usize], facts[b as usize]) {
                (Some(Fact::Local(offset)), Some(Fact::Imm(add)))
                | (Some(Fact::Imm(add)), Some(Fact::Local(offset))) => Some((offset, add)),
                _ => None,
            };
            if let Some((offset, add)) = pair {
                // Match target-width unsigned operands; the allocated frame
                // establishes base+offset safety only for an in-frame result.
                if let Some(end) = offset.checked_add(add as u64 as usize).filter(|&end| end <= frame_size) {
                    outputs.push((dst, Fact::Local(end)));
                    outputs.push((overflow, Fact::Imm(0)));
                }
            }
        }
        _ => {},
    }
    crate::registers::visit_registers(op, |_| {}, |r| facts[r as usize] = None);
    for (r, fact) in outputs { facts[r as usize] = Some(fact); }
}

fn block_starts(f: &Function) -> Vec<bool> {
    let mut starts = vec![false; f.code.len()];
    starts[0] = true;
    for (pc, op) in f.code.iter().enumerate() {
        match op {
            Op::Jump { target } => starts[*target] = true,
            Op::Switch { cases, otherwise, .. } => {
                starts[*otherwise] = true;
                for (_, target) in cases { starts[*target] = true; }
            }
            _ => {},
        }
        if matches!(op, Op::Jump {..} | Op::Switch {..} | Op::Return | Op::Trap {..}) && pc+1 < starts.len() {
            starts[pc+1] = true;
        }
    }
    starts
}

pub(super) fn collect(f: &Function, program: &Program) -> BTreeMap<usize, Vec<Option<usize>>> {
    collect_with_work(f, program, MAX_WORK)
}

fn collect_with_work(f: &Function, program: &Program, max_work: usize) -> BTreeMap<usize, Vec<Option<usize>>> {
    collect_with_policy(f,program,max_work,None)
}
#[cfg(feature = "jit-parameterized-literals")]
pub(super) fn collect_with_literals(f:&Function,program:&Program,literals:&std::collections::BTreeSet<usize>)->BTreeMap<usize,Vec<Option<usize>>> {
    collect_with_policy(f,program,MAX_WORK,Some(literals))
}
fn collect_with_policy(f:&Function,program:&Program,max_work:usize,literals:Option<&std::collections::BTreeSet<usize>>)->BTreeMap<usize,Vec<Option<usize>>> {
    let mut result = BTreeMap::new();
    if f.code.is_empty() || f.code.len() > MAX_OPS || f.registers > MAX_REGISTERS { return result; }
    let starts = block_starts(f);
    let resets = starts.iter().filter(|&&start| start).count();
    let Some(mut work) = f.registers.checked_mul(resets).and_then(|n| n.checked_add(f.code.len())) else { return result; };
    if work > max_work { return result; }
    let mut facts = vec![None; f.registers];
    for (pc, op) in f.code.iter().enumerate() {
        if starts[pc] { facts.fill(None); }
        if let Op::Call { function, args, .. } = op {
            let Some(next) = work.checked_add(args.len()) else { return BTreeMap::new(); };
            work = next;
            if work > max_work { return BTreeMap::new(); }
            let hints: Vec<_> = args.iter().zip(&program.functions[*function].args).map(|(&r, slot)| {
                match facts[r as usize] {
                    Some(Fact::Local(offset)) if slot.size != 0 && offset.checked_add(slot.size)
                        .is_some_and(|end| end <= f.frame_size) => Some(offset),
                    _ => None,
                }
            }).collect();
            if hints.iter().any(Option::is_some) { result.insert(pc, hints); }
        }
        transfer(op, &mut facts, f.frame_size);
        if literals.is_some_and(|pcs|pcs.contains(&pc)) {
            let Op::Imm{dst,..}=op else {unreachable!("literal selection must refer to Imm")};
            facts[*dst as usize]=None;
        }
    }
    result
}

#[cfg(test)]
#[path="call_slots_tests.rs"]
mod tests;
