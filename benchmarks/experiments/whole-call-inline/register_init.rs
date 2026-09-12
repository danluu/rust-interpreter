//! Bounded definite-initialization proof, called only on validated functions.
//! A true result means every reachable read follows a complete register write
//! on every path from function entry. False includes resource exhaustion.
use crate::{Function, Op};
use std::collections::VecDeque;

#[derive(Clone, Copy)]
struct Bounds { registers: usize, operations: usize, blocks: usize, cells: usize, edges: usize, work: usize }
const BOUNDS: Bounds = Bounds { registers: 65_536, operations: 500_000, blocks: 8192,
    cells: 262_144, edges: 131_072, work: 8_000_000 };

pub(crate) fn proves_initialized(f: &Function) -> bool {
    prove(f, BOUNDS).unwrap_or(false)
}

fn prove(f: &Function, bounds: Bounds) -> Option<bool> {
    if f.code.is_empty() || f.registers > bounds.registers || f.code.len() > bounds.operations { return None; }
    let mut work = bounds.work;
    let charge = |work: &mut usize, cost| -> Option<()> { *work = work.checked_sub(cost)?; Some(()) };
    charge(&mut work, f.code.len())?;
    let mut starts = vec![false; f.code.len()]; starts[0] = true;
    for (pc, op) in f.code.iter().enumerate() {
        match op {
            Op::Jump { target } => starts[*target] = true,
            Op::Switch { cases, otherwise, .. } => {
                charge(&mut work, cases.len())?;
                starts[*otherwise] = true;
                for (_, target) in cases { starts[*target] = true; }
            }
            _ => {}
        }
        if matches!(op, Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }) && pc + 1 < starts.len() {
            starts[pc + 1] = true;
        }
    }
    let positions: Vec<_> = starts.iter().enumerate().filter_map(|(pc, start)| start.then_some(pc)).collect();
    let n = positions.len();
    let words = f.registers.div_ceil(64).max(1);
    let cells = n.checked_mul(words)?;
    if n > bounds.blocks || cells > bounds.cells { return None; }
    charge(&mut work, cells.checked_mul(4)?)?;
    let mut block_at = vec![0; f.code.len()];
    for b in 0..n {
        let end = positions.get(b+1).copied().unwrap_or(f.code.len());
        block_at[positions[b]..end].fill(b);
    }
    let mut successors = vec![vec![]; n];
    let mut predecessors = vec![vec![]; n];
    let mut edges = 0usize;
    for b in 0..n {
        let end = positions.get(b+1).copied().unwrap_or(f.code.len());
        let mut edge = |pc| -> Option<()> {
            edges += 1;
            if edges > bounds.edges { return None; }
            charge(&mut work, 1)?;
            let target = block_at[pc];
            successors[b].push(target); predecessors[target].push(b); Some(())
        };
        match &f.code[end-1] {
            Op::Jump { target } => edge(*target)?,
            Op::Switch { cases, otherwise, .. } => {
                edge(*otherwise)?;
                for (_, target) in cases { edge(*target)?; }
            }
            Op::Return | Op::Trap { .. } => {}
            _ if end < f.code.len() => edge(end)?,
            // A reachable fall-off is invalid execution, never a positive proof.
            _ => return Some(false),
        }
    }
    let mut reachable = vec![false; n];
    let mut todo = vec![0]; reachable[0] = true;
    while let Some(b) = todo.pop() {
        charge(&mut work, successors[b].len())?;
        for &next in &successors[b] {
            if !reachable[next] { reachable[next] = true; todo.push(next); }
        }
    }
    let mut generated = vec![0u64; cells];
    let mut required = vec![0u64; cells];
    for b in 0..n {
        if !reachable[b] { continue; }
        let end = positions.get(b+1).copied().unwrap_or(f.code.len());
        let row = b * words;
        for op in &f.code[positions[b]..end] {
            let mut writes = [0; 2]; let mut count = 0; let mut reads = 0usize;
            crate::registers::visit_registers(op, |r| {
                reads += 1;
                let word = row + r as usize / 64; let bit = 1u64 << (r % 64);
                if generated[word] & bit == 0 { required[word] |= bit; }
            }, |r| { writes[count] = r; count += 1; });
            // All reads precede every output, including aliased Binary outputs.
            charge(&mut work, 1 + reads + count)?;
            for &r in &writes[..count] { generated[row + r as usize / 64] |= 1u64 << (r % 64); }
        }
    }
    // Must analysis: non-entry states begin at top and only lose facts.
    // Entry is always empty, even with a backedge to block zero. Thus a loop
    // cannot justify its first read using a definition on a later iteration.
    let mut incoming = vec![u64::MAX; cells];
    let mut outgoing = vec![u64::MAX; cells];
    incoming[..words].fill(0); outgoing[..words].copy_from_slice(&generated[..words]);
    let mut queued = reachable.clone();
    let mut queue: VecDeque<_> = (0..n).filter(|&b| reachable[b]).collect();
    while let Some(b) = queue.pop_front() {
        queued[b] = false; let row = b * words; let mut changed = false;
        charge(&mut work, words.checked_mul(predecessors[b].len().checked_add(1)?)?)?;
        for word in 0..words {
            let mut value = if b == 0 { 0 } else { u64::MAX };
            if b != 0 {
                for &p in &predecessors[b] {
                    if reachable[p] { value &= outgoing[p * words + word]; }
                }
            }
            incoming[row + word] = value;
            let output = value | generated[row + word];
            changed |= outgoing[row + word] != output;
            outgoing[row + word] = output;
        }
        if changed {
            charge(&mut work, successors[b].len())?;
            for &next in &successors[b] {
                if !queued[next] { queue.push_back(next); queued[next] = true; }
            }
        }
    }
    charge(&mut work, cells)?;
    Some((0..n).filter(|&b| reachable[b]).all(|b|
        (b*words..(b+1)*words).all(|i| required[i] & !incoming[i] == 0)))
}

#[cfg(test)]
#[path = "register_init_tests.rs"]
mod tests;
