//! Validate exact typed artifact/profile identities, then weight hypothetical slots.
use bincode::Options;
use rust_interp_bytecode::*;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Deserialize)]
struct Profile { functions: Vec<Counts> }
#[derive(Deserialize)]
struct Counts {
    name: String, frame_size: usize, registers: usize, operations: Vec<String>,
    interpreted: Vec<u64>, jit_blocks: Vec<u64>, jit_block_ends: Vec<usize>,
    jit_tree_blocks: Vec<u64>, jit_tree_block_ends: Vec<usize>,
}
#[derive(Deserialize)]
struct Inventory {
    id: usize, name: String, old_local_extent: usize, additional_bytes_saved: usize,
    hypothetical_local_extent: Option<usize>, decline: Option<String>, production_change: bool,
    #[serde(default)] baseline_slots_reconstructed: bool,
    #[serde(default)] arrays: Vec<Array>,
    #[serde(default)] physical_classes: BTreeMap<String, (usize, usize)>,
}
#[derive(Deserialize)]
struct Array {
    local: usize, size: usize, align: usize, original_offset: usize, hypothetical_offset: usize,
    exclusion: Option<String>, eligible: bool,
}

fn frequencies(f: &Function, p: &Counts) -> Result<Vec<u64>, String> {
    if f.name != p.name || f.frame_size != p.frame_size || f.registers != p.registers ||
        [p.operations.len(), p.interpreted.len(), p.jit_blocks.len(), p.jit_block_ends.len(),
            p.jit_tree_blocks.len(), p.jit_tree_block_ends.len()].iter().any(|&n| n != f.code.len()) {
        return Err("profile function identity or dimensions differ".into());
    }
    // Full identity guard only; never parse Debug text to discover operations.
    if !f.code.iter().zip(&p.operations).all(|(op, text)| format!("{op:?}") == *text) {
        return Err("profile operation differs from typed artifact".into());
    }
    let mut result = p.interpreted.clone();
    for (blocks, ends) in [(&p.jit_blocks, &p.jit_block_ends), (&p.jit_tree_blocks, &p.jit_tree_block_ends)] {
        for (pc, &hits) in blocks.iter().enumerate() {
            if hits == 0 { continue; }
            let end = ends[pc];
            if end <= pc || end > f.code.len() { return Err("invalid native profile range".into()); }
            for count in &mut result[pc..end] {
                *count = count.checked_add(hits).ok_or("profile count overflow")?;
            }
        }
    }
    Ok(result)
}

#[derive(Default, Serialize)]
struct Totals {
    direct_calls: u128,
    direct_frame_bytes: u128,
    inventoried_frame_bytes: u128,
    unobserved_frame_bytes: u128,
    planner_declined_frame_bytes: u128,
    old_local_extent_bytes: u128,
    additional_bytes_saved: u128,
    eligible_array_bytes: u128,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 3 { return Err("usage: aggregate-reuse-weights PROGRAM PROFILE INVENTORY".into()); }
    let bytes = std::fs::read(&args[0])?;
    if bytes.len() > 64*1024*1024 { return Err("artifact exceeds limit".into()); }
    let program: Program = bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(64*1024*1024).reject_trailing_bytes().deserialize(&bytes)?;
    validate(&program)?;
    let read = |path: &str| -> Result<std::io::BufReader<std::fs::File>, std::io::Error> {
        Ok(std::io::BufReader::new(std::fs::File::open(path)?))
    };
    let profile: Profile = serde_json::from_reader(read(&args[1])?)?;
    let inventory: Vec<Inventory> = serde_json::from_reader(read(&args[2])?)?;
    if program.functions.len() != profile.functions.len() { return Err("profile function count differs".into()); }
    let mut by_id = BTreeMap::new();
    for row in &inventory {
        let f = program.functions.get(row.id).ok_or("inventory ID outside artifact")?;
        if row.production_change || f.name != row.name || row.old_local_extent > f.frame_size || by_id.insert(row.id, row).is_some() {
            return Err("inventory identity/extent differs or ID repeated".into());
        }
        if row.decline.is_none() {
            let end = row.hypothetical_local_extent.ok_or("missing hypothetical extent")?;
            if !row.baseline_slots_reconstructed || row.additional_bytes_saved != row.old_local_extent.saturating_sub(end) {
                return Err("uncertified hypothetical extent".into());
            }
            let mut original: Vec<_> = row.arrays.iter().map(|a| (a.original_offset, a.size, a.local)).collect();
            original.sort_unstable();
            let mut previous = 0;
            for (at, size, _) in original {
                if size == 0 || at < previous { return Err("original array ranges overlap".into()); }
                previous = at.checked_add(size).ok_or("array extent overflow")?;
            }
            for a in &row.arrays {
                if !a.align.is_power_of_two() || a.original_offset % a.align != 0 || a.hypothetical_offset % a.align != 0 ||
                    a.original_offset.checked_add(a.size).is_none_or(|end| end > row.old_local_extent) ||
                    a.hypothetical_offset.checked_add(a.size).is_none_or(|e| e > end) || a.eligible != a.exclusion.is_none() {
                    return Err("invalid array extent or eligibility".into());
                }
            }
        } else if row.additional_bytes_saved != 0 { return Err("declined analysis claims savings".into()); }
    }
    let mut instructions = 0u128;
    let mut calls = vec![0u128; program.functions.len()];
    let mut indirect = 0u128;
    for (f, p) in program.functions.iter().zip(&profile.functions) {
        let counts = frequencies(f, p)?;
        instructions += counts.iter().map(|&n| n as u128).sum::<u128>();
        for (op, count) in f.code.iter().zip(counts) {
            match op {
                Op::Call { function, .. } => calls[*function] += count as u128,
                Op::CallIndirect { .. } => indirect += count as u128,
                _ => {},
            }
        }
    }
    let mut totals = Totals::default();
    let mut reasons = BTreeMap::<String, u128>::new();
    let mut classes = BTreeMap::<String, u128>::new();
    let mut rows = vec![];
    for (id, &count) in calls.iter().enumerate() {
        if count == 0 { continue; }
        let f = &program.functions[id];
        let frame = count * f.frame_size.max(1) as u128;
        totals.direct_calls += count; totals.direct_frame_bytes += frame;
        let Some(row) = by_id.get(&id) else { totals.unobserved_frame_bytes += frame; continue; };
        totals.inventoried_frame_bytes += frame;
        totals.old_local_extent_bytes += count * row.old_local_extent as u128;
        totals.additional_bytes_saved += count * row.additional_bytes_saved as u128;
        if row.decline.is_some() { totals.planner_declined_frame_bytes += frame; }
        for a in &row.arrays {
            let bytes = count * a.size as u128;
            if a.eligible { totals.eligible_array_bytes += bytes; }
            else { *reasons.entry(a.exclusion.clone().unwrap()).or_default() += bytes; }
        }
        for (class, (_, bytes)) in &row.physical_classes { *classes.entry(class.clone()).or_default() += count * *bytes as u128; }
        rows.push(serde_json::json!({"id":id,"name":f.name,"calls":count,"frame_size":f.frame_size,
            "frame_bytes":frame,"old_local_extent":row.old_local_extent,
            "additional_bytes_saved_per_call":row.additional_bytes_saved,
            "weighted_additional_bytes_saved":count * row.additional_bytes_saved as u128,
            "decline":row.decline}));
    }
    println!("{}", serde_json::to_string_pretty(&serde_json::json!({
        "instructions":instructions,"totals":totals,"indirect_calls_without_target_attribution":indirect,
        "array_exclusion_bytes":reasons,"physical_layout_class_bytes":classes,"callees":rows,
        "inventory_ids_checked":inventory.len(),"production_change":false,"performance_measurement":false,
        "limitation":"Hypothetical local extents weighted by matching direct calls, excluding frame alignment padding, indirect targets and entry/TLS frames. Does not predict memset cost or speedup; final frame alignment/temp layout has not been transformed."
    }))?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (Function, Counts) {
        let code=vec![Op::Local {dst:0,offset:0},Op::Imm {dst:1,value:1},Op::Store {address:0,src:1,size:8},Op::Return];
        let p=Counts {name:"range".into(),frame_size:16,registers:2,operations:code.iter().map(|op|format!("{op:?}")).collect(),
            interpreted:vec![0,1,0,2],jit_blocks:vec![2,0,0,0],jit_block_ends:vec![3,0,0,0],
            jit_tree_blocks:vec![1,0,0,1],jit_tree_block_ends:vec![3,0,0,4]};
        (Function {name:"range".into(),frame_size:16,frame_align:16,registers:2,args:vec![],result:Slot {offset:0,size:8},code},p)
    }
    #[test]
    fn counts_all_three_execution_paths_with_their_own_boundaries() {
        let (f,p)=fixture(); assert_eq!(frequencies(&f,&p).unwrap(),[3,4,3,3]);
    }
    #[test]
    fn rejects_stale_operations_and_invalid_tree_ranges() {
        let (f,mut p)=fixture();p.operations[1]="different".into();assert!(frequencies(&f,&p).is_err());
        let (_,mut p)=fixture();p.jit_tree_block_ends[3]=5;assert!(frequencies(&f,&p).is_err());
    }
    #[test]
    fn rejects_overflow_and_wrong_profile_dimensions() {
        let (f,mut p)=fixture();p.interpreted[0]=u64::MAX;assert!(frequencies(&f,&p).is_err());
        let (_,mut p)=fixture();p.jit_blocks.pop();assert!(frequencies(&f,&p).is_err());
    }
}
