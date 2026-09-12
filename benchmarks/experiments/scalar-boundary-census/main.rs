//! Join typed boundary observations to exact original bytecode/profiles.
use bincode::Options;
use rust_interp_bytecode::{Binary, Function, Op, Program, Reg, Slot, diagnostic_visit_registers, validate};
use serde::Deserialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
mod profile;
use profile::{Fact, Profile, block_starts, frequencies, transfer};

#[derive(Deserialize)]
struct Inventory {
    schema_version: u32, diagnostic_only: bool, boundary_rows: usize,
    program_functions: usize, functions: Vec<Observed>,
}
#[derive(Deserialize)]
struct Observed {
    function_id: usize, function_sha256: String, args: Vec<Slot>, result: Slot,
    status: String, rows: Vec<Value>, ordinary_private_primitive_slots: usize,
    spread_argument: bool, synthetic_caller_location: bool,
}
fn slot(s: &Slot) -> (usize, usize) { (s.offset, s.size) }
fn category(row: &Value) -> &'static str {
    if row["eligible_primitive"] == true { "eligible_primitive" }
    else if row["eligible_scalar_layout"] == true { "eligible_other_scalar" }
    else if row["primitive"] == true { "rejected_primitive" }
    else if row["scalar_layout"] == true { "rejected_other_scalar" }
    else { "non_scalar" }
}

fn check_inventory(program: &Program, inventory: &Inventory) -> Result<(), String> {
    if inventory.schema_version != 1 || !inventory.diagnostic_only || inventory.program_functions != program.functions.len()
        || inventory.functions.len() > 10_000 || inventory.boundary_rows > 32_768
        || inventory.functions.iter().map(|f| f.rows.len()).sum::<usize>() != inventory.boundary_rows {
        return Err("observer dimensions or schema differ".into());
    }
    let mut seen = std::collections::BTreeSet::new();
    for observed in &inventory.functions {
        let f = program.functions.get(observed.function_id).ok_or("observer function out of range")?;
        if !seen.insert(observed.function_id) || format!("{:x}", Sha256::digest(bincode::serialize(f).map_err(|e| e.to_string())?)) != observed.function_sha256
            || !observed.args.iter().map(slot).eq(f.args.iter().map(slot)) || slot(&observed.result) != slot(&f.result)
            || !matches!(observed.status.as_str(), "observed" | "analysis_bound_exceeded") {
            return Err("observer exact function identity differs".into());
        }
        let mut locals = std::collections::BTreeSet::new();
        for row in &observed.rows {
            let local = row["local"].as_u64().ok_or("missing typed local ID")?;
            if !locals.insert(local) { return Err("duplicate typed local".into()); }
            if row["abi_binding"] != true {
                if !row["slot"].is_null() || row["eligible_primitive"] == true || row["eligible_scalar_layout"] == true {
                    return Err("unbound row claims a final slot or eligibility".into());
                }
                continue;
            }
            let actual: Slot = serde_json::from_value(row["slot"].clone()).map_err(|e| e.to_string())?;
            let expected = if row["role"] == "result" && local == 0 { &f.result }
            else if row["role"] == "argument" && local != 0 {
                let ids = row["abi_argument_indices"].as_array().ok_or("missing ABI indices")?;
                if ids.len() != 1 { return Err("ambiguous ABI index".into()); }
                f.args.get(ids[0].as_u64().ok_or("invalid ABI index")? as usize).ok_or("ABI index out of range")?
            } else { return Err("invalid typed role".into()); };
            if slot(&actual) != slot(expected) { return Err("typed slot does not match ABI".into()); }
        }
    }
    Ok(())
}

type Counts = BTreeMap<String, u128>;
fn add(counts: &mut Counts, key: &str, value: u128) { *counts.entry(key.into()).or_default() += value; }
fn weighted(counts: &mut Counts, key: &str, native: u64, interpreted: u64, size: usize) {
    add(counts, &format!("{key}_hits"), native as u128 + interpreted as u128);
    add(counts, &format!("{key}_bytes"), (native as u128 + interpreted as u128) * size as u128);
    add(counts, &format!("{key}_native_hits"), native as u128);
    add(counts, &format!("{key}_native_bytes"), native as u128 * size as u128);
}

fn overlap(offset: usize, size: usize, boundary: Slot) -> Option<bool> {
    let end = offset.checked_add(size)?;
    let boundary_end = boundary.offset.checked_add(boundary.size)?;
    (size != 0 && boundary.size != 0 && offset < boundary_end && boundary.offset < end)
        .then_some(offset == boundary.offset && size == boundary.size)
}

fn memory(kind: &str, address: Reg, size: usize, facts: &[Option<Fact>], f: &Function,
    rows: &[Value], counts: &mut [Counts], totals: &mut Counts, j: u64, i: u64) {
    weighted(totals, kind, j, i, size);
    let local = facts.get(address as usize).and_then(|v| match v { Some(Fact::Local(at)) => Some(*at), _ => None });
    let Some(at) = local.filter(|at| at.checked_add(size).is_some_and(|end| end <= f.frame_size)) else {
        weighted(totals, &format!("{kind}_unknown_or_nonframe_address"), j, i, size);
        return;
    };
    weighted(totals, &format!("{kind}_known_frame_address"), j, i, size);
    let mut touches = false;
    for (row, counts) in rows.iter().zip(counts) {
        if row["slot"].is_null() { continue; }
        let boundary: Slot = serde_json::from_value(row["slot"].clone()).expect("validated slot");
        if let Some(full) = overlap(at, size, boundary) {
            touches = true;
            // Bytes describe this access's width, not distinct bytes saved.
            weighted(counts, &format!("{kind}_{}", if full {"full"} else {"partial"}), j, i, size);
        }
    }
    if touches { weighted(totals, &format!("{kind}_touching_boundary"), j, i, size); }
}

fn census(program: &Program, profile: &Profile, inventory: &Inventory) -> Result<Value, String> {
    validate(program)?;
    check_inventory(program, inventory)?;
    if profile.functions.len() != program.functions.len() { return Err("profile function count differs".into()); }
    let observed: BTreeMap<_, _> = inventory.functions.iter().map(|f| (f.function_id, f)).collect();
    let mut totals = Counts::new();
    let mut boundary = Counts::new();
    let mut rows_out = vec![];
    let mut unknown_functions = vec![];
    for (id, (f, p)) in program.functions.iter().zip(&profile.functions).enumerate() {
        let native = frequencies(f, p)?;
        let starts = block_starts(f);
        let rows = observed.get(&id).map(|o| o.rows.as_slice()).unwrap_or(&[]);
        let declined = f.registers > 65_536 || f.code.len() > 500_000 ||
            f.registers.saturating_mul(starts.iter().filter(|&&s| s).count()) > 4_000_000 ||
            rows.len().saturating_mul(f.code.len()) > 4_000_000;
        if declined { unknown_functions.push(id); }
        let mut facts = vec![None; if declined { 0 } else { f.registers }];
        let mut counts = vec![Counts::new(); rows.len()];
        for (pc, op) in f.code.iter().enumerate() {
            if starts[pc] { facts.fill(None); }
            let j = native[pc]; let i = p.interpreted[pc];
            let hits = j as u128 + i as u128;
            add(&mut totals, "instructions", hits);
            add(&mut totals, "native_instructions", j as u128);
            add(&mut totals, "interpreted_instructions", i as u128);
            if hits == 0 {
                if !declined { transfer(op, &mut facts, f.frame_size); }
                continue;
            }
            match op {
                Op::Load { address, size, .. } => memory("load", *address, usize::from(*size), &facts, f, rows, &mut counts, &mut totals, j, i),
                Op::Store { address, size, .. } => memory("store", *address, usize::from(*size), &facts, f, rows, &mut counts, &mut totals, j, i),
                Op::Copy { src, dst, size } => {
                    memory("copy_read", *src, *size, &facts, f, rows, &mut counts, &mut totals, j, i);
                    memory("copy_write", *dst, *size, &facts, f, rows, &mut counts, &mut totals, j, i);
                }
                Op::Call { function, .. } => {
                    add(&mut totals, "direct_calls", hits); add(&mut totals, "native_direct_calls", j as u128);
                    let callee = &program.functions[*function];
                    let typed = observed.get(function);
                    for (index, arg) in callee.args.iter().enumerate() {
                        let row = typed.and_then(|o| o.rows.iter().find(|r| r["role"]=="argument" && r["abi_binding"]==true && r["abi_argument_indices"]==json!([index])));
                        let cat = row.map(category).unwrap_or("uncovered");
                        weighted(&mut boundary, &format!("argument_{cat}"), j, i, arg.size);
                    }
                    // Call counts are attempted result copies. Actual successful
                    // returns are counted separately below, by callee identity.
                    weighted(&mut boundary, "direct_potential_result", j, i, callee.result.size);
                }
                Op::CallIndirect { arg_sizes, result_size, .. } => {
                    add(&mut totals, "indirect_calls", hits); add(&mut totals, "native_indirect_calls", j as u128);
                    for size in arg_sizes { weighted(&mut boundary, "indirect_argument_unresolved_callee", j, i, *size); }
                    weighted(&mut boundary, "indirect_potential_result_unresolved_callee", j, i, *result_size);
                }
                Op::Return => {
                    add(&mut totals, "returns", hits); add(&mut totals, "native_returns", j as u128);
                    let row = rows.iter().find(|r| r["role"]=="result");
                    weighted(&mut boundary, &format!("result_{}", row.map(category).unwrap_or("uncovered")), j, i, f.result.size);
                }
                Op::RandomBytes {..} => add(&mut totals, "random_events", hits),
                _ => {},
            }
            if !declined { transfer(op, &mut facts, f.frame_size); }
        }
        for (row, counts) in rows.iter().zip(counts) {
            rows_out.push(json!({"function_id":id,"function_sha256":observed[&id].function_sha256,
                "typed":row,"category":category(row),"accesses":counts}));
        }
    }
    let coverage = json!({"observed_functions":inventory.functions.len(),"program_functions":program.functions.len(),
        "analysis_bound_exceeded":inventory.functions.iter().filter(|f| f.status!="observed").map(|f| f.function_id).collect::<Vec<_>>(),
        "address_analysis_declined":unknown_functions,"boundary_rows":inventory.boundary_rows,
        "spread_functions":inventory.functions.iter().filter(|f| f.spread_argument).count(),
        "synthetic_caller_location_functions":inventory.functions.iter().filter(|f| f.synthetic_caller_location).count(),
        "ordinary_private_primitive_slots":inventory.functions.iter().map(|f| f.ordinary_private_primitive_slots).sum::<usize>()});
    Ok(json!({"totals":totals,"boundary":boundary,"rows":rows_out,"coverage":coverage,
        "performance_measurement":false,"note":"Typed boundary associations with block-local address facts. Unknown addresses and indirect callees remain uncovered. Partial accesses are reported separately. Counts do not forecast latency."}))
}

fn read_limited(path: &str, limit: u64) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    if std::fs::metadata(path)?.len() > limit { return Err("input exceeds bound".into()); }
    let bytes = std::fs::read(path)?;
    if bytes.len() as u64 > limit { return Err("input grew past bound".into()); }
    Ok(bytes)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len()!=4 { return Err("usage: scalar-boundary-census PROGRAM PROFILE INVENTORY EXPECTED_INSTRUCTIONS".into()); }
    let program: Program = bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
        .reject_trailing_bytes().deserialize(&read_limited(&args[0], 64*1024*1024)?)?;
    let profile: Profile = serde_json::from_slice(&read_limited(&args[1], 128*1024*1024)?)?;
    let inventory: Inventory = serde_json::from_slice(&read_limited(&args[2], 32*1024*1024)?)?;
    let report = census(&program, &profile, &inventory)?;
    if report["totals"]["instructions"].as_u64().map(u128::from) != Some(args[3].parse::<u128>()?) {
        return Err("exact profile instruction total differs".into());
    }
    serde_json::to_writer_pretty(std::io::stdout().lock(), &report)?;
    Ok(())
}

#[cfg(test)]
#[path="census_tests.rs"]
mod tests;
