//! Prospective bounded check reuse, counted without changing the emitter.
use crate::{Binary, Function, Op, Program, Reg};
use serde::Serialize;
use std::collections::BTreeMap;

const CAPACITY: usize = 16;
const MAX_FUNCTION: usize = 65_536;
const MAX_FUNCTION_WORK: usize = 4_000_000;
const MAX_TOTAL_WORK: usize = 32_000_000;

#[derive(Clone, Copy)]
enum Symbol { Local(usize), Imm(u128) }

#[derive(Clone, Copy, Default)]
struct Checked { read: usize, write: usize, read_pc: usize, write_pc: usize }

#[derive(Default, Serialize)]
struct Counts {
    accesses: u64,
    known_local: u64,
    baseline_checks: u64,
    reusable_checks: u64,
    permission_upgrades: u64,
    definition_invalidations: u64,
    capacity_clears: u64,
}

fn add(to: &mut u64, value: u64) -> Result<(), String> {
    *to = to.checked_add(value).ok_or("address census count overflow")?;
    Ok(())
}

impl Counts {
    fn merge(&mut self, other: &Self) -> Result<(), String> {
        for (to, value) in [(&mut self.accesses, other.accesses),
            (&mut self.known_local, other.known_local),
            (&mut self.baseline_checks, other.baseline_checks),
            (&mut self.reusable_checks, other.reusable_checks),
            (&mut self.permission_upgrades, other.permission_upgrades),
            (&mut self.definition_invalidations, other.definition_invalidations),
            (&mut self.capacity_clears, other.capacity_clears)] { add(to, value)?; }
        Ok(())
    }
}

#[derive(Serialize)]
struct Site { start: usize, pc: usize, prior_pc: usize, register: Reg, size: usize, write: bool, hits: u64 }

fn outputs(op: &Op, symbols: &BTreeMap<Reg, Symbol>, frame_size: usize) -> Vec<(Reg, Symbol)> {
    match *op {
        Op::Local { dst, offset } => vec![(dst, Symbol::Local(offset))],
        Op::Imm { dst, value } => vec![(dst, Symbol::Imm(value))],
        Op::Binary { dst, overflow, op, a, b, bits, signed } => {
            let value = match (symbols.get(&a).copied(), symbols.get(&b).copied()) {
                (Some(Symbol::Imm(a)), Some(Symbol::Imm(b))) => crate::binary(op, a, b, bits, signed)
                    .ok().map(|(v, flag)| (Symbol::Imm(v), flag)),
                (Some(Symbol::Local(offset)), Some(Symbol::Imm(add)))
                | (Some(Symbol::Imm(add)), Some(Symbol::Local(offset)))
                    if matches!(op, Binary::Add) && bits == 64 && !signed => {
                    offset.checked_add(add as u64 as usize).filter(|&end| end <= frame_size)
                        .map(|end| (Symbol::Local(end), false))
                }
                _ => None,
            };
            value.map_or_else(Vec::new, |(value, flag)|
                vec![(dst, value), (overflow, Symbol::Imm(flag as u128))])
        }
        _ => vec![],
    }
}

fn opaque(op: &Op) -> bool {
    // Unknown/new effects reset the prospective proof conservatively.
    !matches!(op, Op::Imm {..} | Op::Local {..} | Op::Load {..} | Op::Store {..}
        | Op::Binary {..} | Op::Unary {..} | Op::Cast {..} | Op::Select {..}
        | Op::Jump {..} | Op::Switch {..} | Op::Assert {..} | Op::Return | Op::Trap {..}
        | Op::Copy {..} | Op::CopyDynamic {..} | Op::FillBytes {..} | Op::CompareBytes {..}
        | Op::FloatBinary {..} | Op::FloatUnary {..} | Op::FloatConvert {..})
}

fn interval_cost(f: &Function, intervals: &[(usize, usize, u64)], limit: usize) -> Option<usize> {
    if f.code.len() > MAX_FUNCTION || f.registers > MAX_FUNCTION { return None; }
    intervals.iter().try_fold(0usize, |sum, &(start, end, _)| {
        f.code[start..end].iter().try_fold(sum, |sum, op| {
            let operands = match op {
                Op::Call { args, .. } => args.len().checked_add(1)?,
                Op::CallIndirect { args, .. } => args.len().checked_add(2)?,
                _ => 7,
            };
            sum.checked_add(operands).filter(|&n| n <= limit)
        })
    })
}

fn interval(f: &Function, start: usize, end: usize, hits: u64, counts: &mut Counts,
    sites: &mut Vec<Site>) -> Result<(), String> {
    let mut symbols = BTreeMap::new();
    let mut checked: BTreeMap<Reg, Checked> = BTreeMap::new();
    for pc in start..end {
        let op = &f.code[pc];
        let access = match *op {
            Op::Load { address, size, .. } => Some((address, usize::from(size), false)),
            Op::Store { address, size, .. } => Some((address, usize::from(size), true)),
            _ => None,
        };
        if let Some((reg, size, write)) = access.filter(|(_, size, _)| *size != 0) {
            add(&mut counts.accesses, hits)?;
            let local = matches!(symbols.get(&reg), Some(Symbol::Local(offset))
                if offset.checked_add(size).is_some_and(|end| end <= f.frame_size));
            if local { add(&mut counts.known_local, hits)?; }
            else {
                add(&mut counts.baseline_checks, hits)?;
                let prior = checked.get(&reg).copied().unwrap_or_default();
                let reusable = if write { prior.write >= size } else { prior.read >= size };
                if reusable {
                    add(&mut counts.reusable_checks, hits)?;
                    sites.push(Site { start, pc, prior_pc: if write { prior.write_pc } else { prior.read_pc },
                        register: reg, size, write, hits });
                } else if write && prior.read >= size { add(&mut counts.permission_upgrades, hits)?; }
                if !checked.contains_key(&reg) && checked.len() == CAPACITY {
                    checked.clear();
                    add(&mut counts.capacity_clears, hits)?;
                }
                let range = checked.entry(reg).or_default();
                if size > range.read { range.read = size; range.read_pc = pc; }
                if write && size > range.write { range.write = size; range.write_pc = pc; }
            }
        }
        // Read all old operands before invalidating aliased outputs. The
        // overflow output remains last, just as in the emitter/interpreter.
        let next = outputs(op, &symbols, f.frame_size);
        let mut invalidations = 0;
        crate::registers::visit_registers(op, |_| {}, |r| {
            symbols.remove(&r);
            invalidations += u64::from(checked.remove(&r).is_some());
        });
        add(&mut counts.definition_invalidations,
            hits.checked_mul(invalidations).ok_or("address census count overflow")?)?;
        for (reg, symbol) in next { symbols.insert(reg, symbol); }
        if opaque(op) { symbols.clear(); checked.clear(); }
    }
    Ok(())
}

pub(super) fn census(program: &Program, bytes: &[u8]) -> Result<serde_json::Value, String> {
    crate::validate(program)?;
    let profile = super::register_width_profile::parse(program, bytes)?;
    let mut total = Counts::default();
    let mut rows = vec![];
    let mut declined = vec![];
    let mut work = 0usize;
    for (id, (f, observed)) in program.functions.iter().zip(&profile.functions).enumerate() {
        let intervals: Vec<_> = observed.intervals().collect();
        if intervals.is_empty() { continue; }
        let cost = interval_cost(f, &intervals,
            MAX_FUNCTION_WORK.min(MAX_TOTAL_WORK.saturating_sub(work)));
        if cost.is_none() {
            declined.push(serde_json::json!({"function": id, "name": f.name,
                "reason": "function or total analysis bound", "opportunities": null}));
            continue;
        }
        work += cost.unwrap();
        let mut counts = Counts::default();
        let mut sites = vec![];
        for (start, end, hits) in intervals { interval(f, start, end, hits, &mut counts, &mut sites)?; }
        total.merge(&counts)?;
        sites.sort_by_key(|s| (std::cmp::Reverse(s.hits), s.pc, s.start));
        sites.truncate(20);
        rows.push(serde_json::json!({"function": id, "name": f.name, "counts": counts, "top_sites": sites}));
    }
    rows.sort_by_key(|r| std::cmp::Reverse(r["counts"]["reusable_checks"].as_u64().unwrap()));
    Ok(serde_json::json!({"schema_version": 1, "status": "counted", "cache_entries": CAPACITY,
        "counts": total, "functions": rows, "declined_functions": declined, "analysis_work": work,
        "guest_instructions_executed": 0, "emitter_changed": false,
        "scope": "Positive-size Load/Store bytecode observations weighted by recorded native interval entries. Existing local facts excluded; exact-register cache resets at each interval. Not hardware traffic, retired instructions, latency, or an implemented check-removal proof."}))
}

#[cfg(test)]
mod tests;
