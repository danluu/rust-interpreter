//! Diagnostic only: whole-call opportunities in exact typed/profile inputs.
use bincode::Options;
use rust_interp_bytecode::{Binary, Function, Op, Program, Reg, Slot, diagnostic_visit_registers, validate};
#[path = "../../../crates/bytecode/src/registers.rs"]
mod registers;
mod opportunities;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

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
    diagnostic_visit_registers(op, |_| {}, |r| facts[r as usize] = None);
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

fn in_frame(facts: &[Option<Fact>], r: Reg, size: usize, frame_size: usize) -> bool {
    matches!(facts[r as usize], Some(Fact::Local(offset))
        if offset.checked_add(size).is_some_and(|end| end <= frame_size))
}

#[derive(Clone, Deserialize)]
struct Profile { functions: Vec<Counts> }
#[derive(Clone, Deserialize)]
struct Counts {
    name: String, frame_size: usize, registers: usize, operations: Vec<String>,
    interpreted: Vec<u64>, jit_blocks: Vec<u64>, jit_block_ends: Vec<usize>,
    jit_tree_blocks: Vec<u64>, jit_tree_block_ends: Vec<usize>,
}

fn frequencies(f: &Function, p: &Counts) -> Result<Vec<u64>, String> {
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
    let mut native = vec![0u64; n];
    for (hits, ends) in [(&p.jit_blocks, &p.jit_block_ends), (&p.jit_tree_blocks, &p.jit_tree_block_ends)] {
        for (pc, (&count, &end)) in hits.iter().zip(ends).enumerate() {
            if end > n || (end != 0 && end <= pc) || (count != 0 && end == 0) {
                return Err("invalid native profile interval".into());
            }
            if count == 0 { continue; }
            for value in &mut native[pc..end] {
                *value = value.checked_add(count).ok_or("native profile count overflow")?;
            }
        }
    }
    Ok(native)
}

#[derive(Default, Serialize)]
struct Totals {
    calls: u128, native_calls: u128, interpreted_calls: u128,
    nonempty_argument_checks: u128, local_argument_checks: u128,
    argument_bytes: u128, local_argument_bytes: u128, zero_size_arguments: u128,
    native_argument_checks: u128, native_local_argument_checks: u128,
    native_argument_bytes: u128, native_local_argument_bytes: u128,
    potential_result_bytes: u128, potential_local_result_bytes: u128,
    native_nonempty_results: u128, native_local_results: u128,
    callee_frame_bytes: u128, analysis_declined_calls: u128,
}

#[derive(Serialize)]
struct CallSite {
    function: usize, pc: usize, callee: Option<usize>, native: u64, interpreted: u64,
    argument_sizes: Vec<usize>, local_arguments: Vec<bool>,
    result_size: usize, local_result: bool, analysis_declined: bool,
}

fn observe(f: &Function, facts: &[Option<Fact>], sizes: &[usize], args: &[Reg], destination: Reg,
           result_size: usize, native: u64, interpreted: u64, frame: Option<usize>, declined: bool,
           totals: &mut Totals) -> (Vec<bool>, bool) {
    let hits = native as u128 + interpreted as u128;
    totals.calls += hits; totals.native_calls += native as u128;
    totals.interpreted_calls += interpreted as u128;
    if declined { totals.analysis_declined_calls += hits; }
    if let Some(size) = frame { totals.callee_frame_bytes += hits * size.max(1) as u128; }
    let mut local = vec![];
    for (&size, &reg) in sizes.iter().zip(args) {
        let known = !declined && in_frame(facts, reg, size, f.frame_size);
        local.push(known);
        if size == 0 { totals.zero_size_arguments += hits; continue; }
        totals.nonempty_argument_checks += hits;
        totals.argument_bytes += hits * size as u128;
        totals.native_argument_checks += native as u128;
        totals.native_argument_bytes += native as u128 * size as u128;
        if known {
            totals.local_argument_checks += hits; totals.local_argument_bytes += hits * size as u128;
            totals.native_local_argument_checks += native as u128;
            totals.native_local_argument_bytes += native as u128 * size as u128;
        }
    }
    let result = !declined && in_frame(facts, destination, result_size, f.frame_size);
    totals.potential_result_bytes += hits * result_size as u128;
    if result { totals.potential_local_result_bytes += hits * result_size as u128; }
    if result_size != 0 {
        totals.native_nonempty_results += native as u128;
        if result { totals.native_local_results += native as u128; }
    }
    (local, result)
}

#[derive(Serialize)]
struct Report {
    instructions: u128, native_instructions: u128, interpreted_instructions: u128,
    native_returns: u128, interpreted_returns: u128, random_events: u128,
    totals: BTreeMap<&'static str, Totals>, sites: Vec<CallSite>,
    declined_functions: Vec<usize>, performance_measurement: bool,
}

fn census(program: &Program, profile: &Profile) -> Result<Report, String> {
    validate(program)?;
    if program.functions.len() != profile.functions.len() { return Err("profile function count differs".into()); }
    let mut report = Report { instructions: 0, native_instructions: 0, interpreted_instructions: 0,
        native_returns: 0, interpreted_returns: 0, random_events: 0,
        totals: BTreeMap::from([("direct", Totals::default()), ("indirect", Totals::default())]),
        sites: vec![], declined_functions: vec![], performance_measurement: false };
    for (id, (f, p)) in program.functions.iter().zip(&profile.functions).enumerate() {
        let native = frequencies(f, p)?;
        let starts = block_starts(f);
        let declined = f.registers > 65_536 || f.code.len() > 500_000 ||
            f.registers.saturating_mul(starts.iter().filter(|&&v| v).count()) > 4_000_000;
        if declined { report.declined_functions.push(id); }
        let mut facts = vec![None; if declined { 0 } else { f.registers }];
        for (pc, op) in f.code.iter().enumerate() {
            if starts[pc] { facts.fill(None); }
            let j = native[pc]; let i = p.interpreted[pc];
            report.native_instructions += j as u128; report.interpreted_instructions += i as u128;
            let call = match op {
                Op::Call { function, args, destination } => {
                    let callee = &program.functions[*function];
                    Some(("direct", Some(*function), args, *destination,
                        callee.args.iter().map(|slot| slot.size).collect::<Vec<_>>(),
                        callee.result.size, Some(callee.frame_size)))
                }
                Op::CallIndirect { args, destination, arg_sizes, result_size, .. } =>
                    Some(("indirect", None, args, *destination, arg_sizes.clone(), *result_size, None)),
                Op::Return => { report.native_returns += j as u128; report.interpreted_returns += i as u128; None }
                Op::RandomBytes {..} => { report.random_events += j as u128 + i as u128; None }
                _ => None,
            };
            if let Some((kind, callee, args, destination, sizes, result_size, frame)) = call {
                let (local_arguments, local_result) = observe(f, &facts, &sizes, args, destination,
                    result_size, j, i, frame, declined, report.totals.get_mut(kind).unwrap());
                if j != 0 || i != 0 {
                    report.sites.push(CallSite { function: id, pc, callee, native: j, interpreted: i,
                        argument_sizes: sizes, local_arguments, result_size, local_result, analysis_declined: declined });
                }
            }
            if !declined { transfer(op, &mut facts, f.frame_size); }
        }
    }
    report.instructions = report.native_instructions + report.interpreted_instructions;
    Ok(report)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 3 { return Err("usage: whole-call-census PROGRAM PROFILE EXPECTED_INSTRUCTIONS".into()); }
    let bytes = std::fs::read(&args[0])?;
    if bytes.len() > 64*1024*1024 { return Err("artifact exceeds limit".into()); }
    let program: Program = bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(64*1024*1024).reject_trailing_bytes().deserialize(&bytes)?;
    let profile: Profile = serde_json::from_reader(std::io::BufReader::new(std::fs::File::open(&args[1])?))?;
    let report = census(&program, &profile)?;
    if report.instructions != args[2].parse::<u128>()? { return Err("profile logical instruction total differs".into()); }
    let opportunities = opportunities::inspect(&program, &report.sites)?;
    serde_json::to_writer_pretty(std::io::stdout().lock(),
        &serde_json::json!({"census":report, "opportunities":opportunities}))?;
    Ok(())
}

#[cfg(test)]
#[path = "../call-slot-census/tests.rs"]
mod tests;
