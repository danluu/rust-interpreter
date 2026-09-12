// Shared diagnostic semantics copied from the qualified whole-call census.
// No operation semantics are inferred from profile strings.
use super::*;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Fact { Local(usize), Imm(u128) }

pub(super) fn transfer(op: &Op, facts: &mut [Option<Fact>], frame_size: usize) {
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
    diagnostic_visit_registers(op, |_| {}, |r| facts[r as usize] = None);
    for (r, fact) in outputs { facts[r as usize] = Some(fact); }
}

pub(super) fn block_starts(f: &Function) -> Vec<bool> {
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

#[derive(Clone, Deserialize)]
pub(super) struct Profile { pub(super) functions: Vec<Counts> }
#[derive(Clone, Deserialize)]
pub(super) struct Counts {
    name: String, frame_size: usize, registers: usize, operations: Vec<String>,
    pub(super) interpreted: Vec<u64>, jit_blocks: Vec<u64>, jit_block_ends: Vec<usize>,
    jit_tree_blocks: Vec<u64>, jit_tree_block_ends: Vec<usize>,
}

pub(super) fn frequencies(f: &Function, p: &Counts) -> Result<Vec<u64>, String> {
    let n = f.code.len();
    if f.name != p.name || f.frame_size != p.frame_size || f.registers != p.registers ||
        [p.operations.len(), p.interpreted.len(), p.jit_blocks.len(), p.jit_block_ends.len(),
            p.jit_tree_blocks.len(), p.jit_tree_block_ends.len()].iter().any(|&len| len != n) {
        return Err("profile function identity or dimensions differ".into());
    }
    // Identity guard only: operation semantics come exclusively from Program.
    if !f.code.iter().zip(&p.operations).all(|(op, text)| format!("{op:?}") == *text) {
        return Err("profile opcode identity differs".into());
    }
    // Event sweep bounds reconstruction to O(operations), even for deeply
    // overlapping valid intervals. Reject any per-PC u64 count overflow.
    let mut incoming = vec![0u128; n+1];
    let mut outgoing = vec![0u128; n+1];
    for (hits, ends) in [(&p.jit_blocks, &p.jit_block_ends), (&p.jit_tree_blocks, &p.jit_tree_block_ends)] {
        for (pc, (&count, &end)) in hits.iter().zip(ends).enumerate() {
            if end > n || (end != 0 && end <= pc) || (count != 0 && end == 0) {
                return Err("invalid native profile interval".into());
            }
            if count == 0 { continue; }
            incoming[pc] += count as u128;
            outgoing[end] += count as u128;
        }
    }
    let mut running = 0u128;
    let mut native = vec![0u64; n];
    for pc in 0..n {
        running = running.checked_sub(outgoing[pc]).ok_or("profile interval underflow")? + incoming[pc];
        native[pc] = u64::try_from(running).map_err(|_| "native profile count overflow")?;
    }
    if running != outgoing[n] { return Err("native profile intervals do not close".into()); }
    Ok(native)
}
