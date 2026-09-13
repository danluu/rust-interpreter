//! Offline must-facts from normal function entry; never seeds native execution.
use crate::{Binary, Function, Op, Program, Reg};
use std::collections::{BTreeMap, BTreeSet, VecDeque};

const MAX_ITEMS: usize = 65_536;
const MAX_EDGES: usize = 262_144;
const MAX_CELLS: usize = 262_144;
const MAX_FUNCTION_WORK: usize = 4_000_000;
const MAX_TOTAL_WORK: usize = 32_000_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Symbol { Local(usize), Imm(u128) }
type Facts = BTreeMap<Reg, Symbol>;

struct Budget { used: usize, limit: usize }
impl Budget {
    fn take(&mut self, n: usize) -> Option<()> {
        self.used = self.used.checked_add(n)?;
        (self.used <= self.limit).then_some(())
    }
}

fn transfer(facts: &mut Facts, op: &Op, frame: usize, budget: &mut Budget) -> Option<()> {
    let next = match *op {
        Op::Local { dst, offset } => vec![(dst, Symbol::Local(offset))],
        Op::Imm { dst, value } => vec![(dst, Symbol::Imm(value))],
        Op::Binary { dst, overflow, op, a, b, bits, signed } => {
            let value = match (facts.get(&a).copied(), facts.get(&b).copied()) {
                (Some(Symbol::Imm(a)), Some(Symbol::Imm(b))) => crate::binary(op, a, b, bits, signed)
                    .ok().map(|(v, flag)| (Symbol::Imm(v), flag)),
                (Some(Symbol::Local(offset)), Some(Symbol::Imm(add)))
                | (Some(Symbol::Imm(add)), Some(Symbol::Local(offset)))
                    if matches!(op, Binary::Add) && bits == 64 && !signed => {
                    offset.checked_add(add as u64 as usize).filter(|&end| end <= frame)
                        .map(|end| (Symbol::Local(end), false))
                }
                _ => None,
            };
            value.map_or_else(Vec::new, |(value, flag)|
                vec![(dst, value), (overflow, Symbol::Imm(flag as u128))])
        }
        _ => vec![],
    };
    let mut operands = 1usize;
    crate::registers::visit_registers(op, |_| operands += 1, |r| { facts.remove(&r); });
    budget.take(operands + next.len())?;
    // Sources were read before any aliased output, with overflow written last.
    for (r, value) in next { facts.insert(r, value); }
    Some(())
}

struct Flow { starts: Vec<usize>, inputs: Vec<Option<Facts>> }

fn analyze(f: &Function, budget: &mut Budget) -> Option<Flow> {
    let n = f.code.len();
    if n == 0 || n > MAX_ITEMS || f.registers > MAX_ITEMS { return None; }
    let mut leaders = BTreeSet::from([0]);
    let mut successors = Vec::with_capacity(n);
    let mut edges = 0usize;
    for (pc, op) in f.code.iter().enumerate() {
        let next = match op {
            Op::Jump { target } => vec![*target],
            Op::Switch { cases, otherwise, .. } => {
                if cases.len() > MAX_EDGES { return None; }
                budget.take(cases.len())?;
                let mut next: Vec<_> = cases.iter().map(|(_, pc)| *pc).chain([*otherwise]).collect();
                next.sort_unstable(); next.dedup(); next
            }
            Op::Return | Op::Trap { .. } => vec![],
            _ if pc + 1 < n => vec![pc + 1],
            _ => vec![],
        };
        budget.take(next.len() + 1)?;
        edges = edges.checked_add(next.len())?;
        if edges > MAX_EDGES || next.iter().any(|&pc| pc >= n) { return None; }
        if matches!(op, Op::Jump {..} | Op::Switch {..} | Op::Return | Op::Trap {..}) {
            leaders.extend(next.iter().copied());
            if pc + 1 < n { leaders.insert(pc + 1); }
        }
        successors.push(next);
    }
    let starts: Vec<_> = leaders.into_iter().collect();
    let mut block_at = vec![0; n];
    for (block, &start) in starts.iter().enumerate() {
        block_at[start..starts.get(block + 1).copied().unwrap_or(n)].fill(block);
    }
    let mut inputs: Vec<Option<Facts>> = vec![None; starts.len()];
    inputs[0] = Some(Facts::new()); // No initial zero or old activation value is assumed.
    let mut pending = VecDeque::from([0]);
    let mut queued = vec![false; starts.len()]; queued[0] = true;
    let mut cells = 0usize;
    while let Some(block) = pending.pop_front() {
        queued[block] = false;
        let mut out = inputs[block].as_ref()?.clone();
        budget.take(out.len())?;
        let end = starts.get(block + 1).copied().unwrap_or(n);
        for op in &f.code[starts[block]..end] { transfer(&mut out, op, f.frame_size, budget)?; }
        for &pc in &successors[end - 1] {
            let next = block_at[pc];
            budget.take(out.len() + inputs[next].as_ref().map_or(0, Facts::len) + 1)?;
            let changed = if let Some(old) = &mut inputs[next] {
                let before = old.len();
                old.retain(|r, value| out.get(r) == Some(value));
                cells -= before - old.len();
                old.len() != before
            } else {
                cells = cells.checked_add(out.len())?;
                if cells > MAX_CELLS { return None; }
                inputs[next] = Some(out.clone()); true
            };
            if changed && !queued[next] { queued[next] = true; pending.push_back(next); }
        }
    }
    Some(Flow { starts, inputs })
}

#[derive(Clone, Copy)]
struct Access { register: Reg, size: usize, write: bool, copy: bool }

fn accesses(op: &Op) -> Vec<Access> {
    match *op {
        Op::Load { address, size, .. } if size != 0 =>
            vec![Access { register: address, size: size.into(), write: false, copy: false }],
        Op::Store { address, size, .. } if size != 0 =>
            vec![Access { register: address, size: size.into(), write: true, copy: false }],
        Op::Copy { dst, src, size } if size != 0 && size <= 128 => vec![
            Access { register: src, size, write: false, copy: true },
            Access { register: dst, size, write: true, copy: true }],
        _ => vec![],
    }
}

fn local(facts: &Facts, access: Access, frame: usize) -> Option<usize> {
    match facts.get(&access.register) {
        Some(Symbol::Local(offset)) if offset.checked_add(access.size).is_some_and(|end| end <= frame) => Some(*offset),
        _ => None,
    }
}

fn function(f: &Function, intervals: &[(usize, usize, u64)], budget: &mut Budget)
    -> Option<serde_json::Value> {
    let flow = analyze(f, budget)?;
    // Retain only memory facts at uses, avoiding a PC-by-register state table.
    let mut global = vec![vec![]; f.code.len()];
    for (block, input) in flow.inputs.iter().enumerate() {
        let Some(mut facts) = input.clone() else { continue; };
        budget.take(facts.len())?;
        let end = flow.starts.get(block + 1).copied().unwrap_or(f.code.len());
        for pc in flow.starts[block]..end {
            global[pc] = accesses(&f.code[pc]).iter().map(|&a| local(&facts, a, f.frame_size)).collect();
            transfer(&mut facts, &f.code[pc], f.frame_size, budget)?;
        }
    }
    let mut total = [0u64; 6];
    let mut sites = vec![];
    for &(start, end, hits) in intervals {
        let mut facts = Facts::new();
        for pc in start..end {
            for (index, access) in accesses(&f.code[pc]).into_iter().enumerate() {
                total[0] = total[0].checked_add(hits)?;
                if local(&facts, access, f.frame_size).is_some() {
                    total[1] = total[1].checked_add(hits)?;
                } else {
                    total[2] = total[2].checked_add(hits)?;
                    if let Some(offset) = global[pc].get(index).copied().flatten() {
                        total[3] = total[3].checked_add(hits)?;
                        total[4] = total[4].checked_add(if access.write { hits } else { 0 })?;
                        total[5] = total[5].checked_add(if access.copy { hits } else { 0 })?;
                        if sites.len() >= MAX_ITEMS { return None; }
                        sites.push(serde_json::json!({"start":start,"pc":pc,"register":access.register,
                            "offset":offset,"size":access.size,"write":access.write,"copy":access.copy,"hits":hits}));
                    }
                }
            }
            transfer(&mut facts, &f.code[pc], f.frame_size, budget)?;
        }
    }
    sites.sort_by_key(|v| std::cmp::Reverse(v["hits"].as_u64().unwrap())); sites.truncate(20);
    Some(serde_json::json!({"weighted_accesses":total[0],"existing_local_accesses":total[1],
        "region_unknown_accesses":total[2],"additional_local_accesses":total[3],
        "additional_writes":total[4],"additional_copy_addresses":total[5],"top_sites":sites}))
}

pub(super) fn census(program: &Program, bytes: &[u8]) -> Result<serde_json::Value, String> {
    crate::validate(program)?;
    let profile = super::register_width_profile::parse(program, bytes)?;
    let mut rows = vec![]; let mut declined = vec![]; let mut work = 0usize;
    for (id, (f, p)) in program.functions.iter().zip(&profile.functions).enumerate() {
        let intervals: Vec<_> = p.intervals().collect();
        if intervals.is_empty() { continue; }
        let mut budget = Budget { used: 0, limit: MAX_FUNCTION_WORK.min(MAX_TOTAL_WORK.saturating_sub(work)) };
        let result = function(f, &intervals, &mut budget);
        work = work.saturating_add(budget.used.min(budget.limit));
        if let Some(mut row) = result {
            row["function"] = id.into(); row["name"] = f.name.clone().into(); rows.push(row);
        } else { declined.push(serde_json::json!({"function":id,"reason":"analysis, count or report bound","opportunities":null})); }
    }
    let mut total = serde_json::Map::new();
    for key in ["weighted_accesses","existing_local_accesses","region_unknown_accesses",
        "additional_local_accesses","additional_writes","additional_copy_addresses"] {
        let sum = rows.iter().try_fold(0u64, |sum, row| sum.checked_add(row[key].as_u64().unwrap()))
            .ok_or("region-fact counter overflow")?;
        total.insert(key.into(), sum.into());
    }
    rows.sort_by_key(|v| std::cmp::Reverse(v["additional_local_accesses"].as_u64().unwrap()));
    Ok(serde_json::json!({"schema_version":1,"status":"counted","counts":total,"functions":rows,
        "declined_functions":declined,"analysis_work":work,"guest_instructions_executed":0,
        "emitter_changed":false,"scope":"Fixed Load/Store and both Copy addresses weighted by exact native intervals. Normal-entry whole-CFG must-facts compared with region-local folding. Not an arbitrary-entry safety proof, native instruction count, latency estimate or implemented optimization."}))
}

#[cfg(test)]
mod tests;
