//! Join new slot inventories to typed artifacts and explicitly historical profiles.
use bincode::Options;
use rust_interp_bytecode::*;
use serde::Deserialize;
use std::collections::BTreeMap;

#[derive(Deserialize)]
struct Profile { functions: Vec<Counts> }
#[derive(Deserialize)]
struct Counts {
    name: String, frame_size: usize, registers: usize, operations: Vec<String>,
    interpreted: Vec<u64>, jit_blocks: Vec<u64>, jit_block_ends: Vec<usize>,
    jit_tree_blocks: Vec<u64>, jit_tree_block_ends: Vec<usize>,
}
#[derive(Clone, Deserialize)]
struct Inventory {
    id: usize, name: String, old_local_extent: usize, additional_bytes_saved: usize,
    hypothetical_local_extent: Option<usize>, decline: Option<String>, production_change: bool,
    baseline_slots_reconstructed: bool, slots: Vec<Storage>,
}
#[derive(Clone, Deserialize)]
struct Storage { local: usize, size: usize, align: usize, original_offset: usize, hypothetical_offset: usize,
    exclusion: Option<String>, eligible: bool }

// Same three-path accounting as the retained aggregate-reuse census. Debug
// strings are compared for full identity only; opcode selection uses typed Op.
fn frequencies(f: &Function, p: &Counts) -> Result<Vec<u64>, String> {
    if f.name != p.name || f.frame_size != p.frame_size || f.registers != p.registers ||
        [p.operations.len(),p.interpreted.len(),p.jit_blocks.len(),p.jit_block_ends.len(),
         p.jit_tree_blocks.len(),p.jit_tree_block_ends.len()].iter().any(|&n| n != f.code.len()) {
        return Err("profile dimensions/identity differ".into());
    }
    if !f.code.iter().zip(&p.operations).all(|(op,text)| format!("{op:?}")==*text) { return Err("profile opcode differs".into()); }
    let mut counts=p.interpreted.clone();
    for (blocks,ends) in [(&p.jit_blocks,&p.jit_block_ends),(&p.jit_tree_blocks,&p.jit_tree_block_ends)] {
        for (pc,&hits) in blocks.iter().enumerate() {
            if hits==0 {continue;}
            let end=ends[pc];if end<=pc || end>f.code.len(){return Err("invalid native range".into());}
            for n in &mut counts[pc..end] {*n=n.checked_add(hits).ok_or("count overflow")?;}
        }
    }
    Ok(counts)
}

fn validate_inventory(f: &Function, row: &Inventory) -> Result<(), String> {
    if row.name!=f.name || row.production_change || row.old_local_extent>f.frame_size {
        return Err("inventory identity/extent differs".into());
    }
    if row.decline.is_some() {
        if row.additional_bytes_saved!=0 || row.hypothetical_local_extent.is_some() {return Err("decline claims savings".into());}
        return Ok(());
    }
    let end=row.hypothetical_local_extent.ok_or("missing hypothetical extent")?;
    if !row.baseline_slots_reconstructed || row.additional_bytes_saved!=row.old_local_extent.saturating_sub(end) {
        return Err("uncertified local extent".into());
    }
    for (i,s) in row.slots.iter().enumerate() {
        if s.local!=i || !s.align.is_power_of_two() || s.align>MAX_ALIGNMENT ||
            s.original_offset%s.align!=0 || s.hypothetical_offset%s.align!=0 ||
            s.original_offset.checked_add(s.size).is_none_or(|e| e>row.old_local_extent) ||
            s.hypothetical_offset.checked_add(s.size).is_none_or(|e| e>end) || s.eligible!=s.exclusion.is_none() {
            return Err("invalid slot identity/extent/eligibility".into());
        }
    }
    // Shared slots must coincide exactly and both be eligible; a dedicated
    // range cannot overlap any other positive-size proposed range.
    let mut ranges:Vec<_>=row.slots.iter().filter(|s|s.size>0).collect();
    ranges.sort_unstable_by_key(|s|(s.hypothetical_offset,s.size));
    let mut previous:Option<&Storage>=None;
    for s in ranges {
        if let Some(p)=previous {
            if p.hypothetical_offset+p.size>s.hypothetical_offset &&
                !(p.hypothetical_offset==s.hypothetical_offset && p.size==s.size && p.align==s.align && p.eligible && s.eligible) {
                return Err("invalid proposed overlap".into());
            }
        }
        previous=Some(s);
    }
    Ok(())
}

fn main()->Result<(),Box<dyn std::error::Error>> {
    let args:Vec<_>=std::env::args().skip(1).collect();
    if args.len()!=3 {return Err("usage: aggregate-byte-write-weights ARTIFACT HISTORICAL_PROFILE INVENTORY".into());}
    let bytes=std::fs::read(&args[0])?;if bytes.len()>64*1024*1024{return Err("oversized artifact".into());}
    let program:Program=bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
        .reject_trailing_bytes().deserialize(&bytes)?;validate(&program)?;
    let reader=|path:&str|std::fs::File::open(path).map(std::io::BufReader::new);
    let profile:Profile=serde_json::from_reader(reader(&args[1])?)?;
    let inventory:Vec<Inventory>=serde_json::from_reader(reader(&args[2])?)?;
    if profile.functions.len()!=program.functions.len(){return Err("profile function count differs".into());}
    let mut by_id=BTreeMap::new();
    for row in &inventory {
        let f=program.functions.get(row.id).ok_or("inventory ID outside artifact")?;
        validate_inventory(f,row)?;
        if by_id.insert(row.id,row).is_some(){return Err("duplicate inventory ID".into());}
    }
    let mut calls=vec![0u128;program.functions.len()];let mut instructions=0u128;let mut indirect=0u128;
    for (f,p) in program.functions.iter().zip(&profile.functions) {
        for (op,n) in f.code.iter().zip(frequencies(f,p)?) {
            instructions+=n as u128;
            match op {Op::Call{function,..}=>calls[*function]+=n as u128,Op::CallIndirect{..}=>indirect+=n as u128,_=>{}}
        }
    }
    let (mut frame_bytes,mut saved,mut unobserved,mut declined)=(0u128,0u128,0u128,0u128);
    let mut rows=vec![];let mut exclusions=BTreeMap::<String,u128>::new();
    for (id,(&count,f)) in calls.iter().zip(&program.functions).enumerate() {
        frame_bytes+=count*f.frame_size.max(1) as u128;
        let Some(row)=by_id.get(&id) else {unobserved+=count*f.frame_size.max(1) as u128;continue;};
        if row.decline.is_some(){declined+=count*f.frame_size.max(1) as u128;}
        let additional=count*row.additional_bytes_saved as u128;saved+=additional;
        for s in &row.slots {
            if let Some(reason)=&s.exclusion {*exclusions.entry(reason.clone()).or_default()+=count*s.size as u128;}
        }
        rows.push(serde_json::json!({"id":id,"name":f.name,"calls":count,"frame_size":f.frame_size,
            "old_local_extent":row.old_local_extent,"hypothetical_local_extent":row.hypothetical_local_extent,
            "additional_bytes_saved_per_call":row.additional_bytes_saved,"weighted_additional_bytes_saved":additional,"decline":row.decline}));
    }
    rows.sort_by_key(|r|std::cmp::Reverse(r["weighted_additional_bytes_saved"].as_u64().unwrap()));
    println!("{}",serde_json::to_string_pretty(&serde_json::json!({"instructions":instructions,
        "direct_calls":calls.iter().sum::<u128>(),"direct_frame_bytes":frame_bytes,"additional_local_bytes_saved":saved,
        "unobserved_direct_frame_bytes":unobserved,"declined_direct_frame_bytes":declined,
        "additional_frame_byte_percentage":100.0*saved as f64/frame_bytes as f64,
        "indirect_calls_without_target_attribution":indirect,"inventories_checked":inventory.len(),
        "exclusion_logical_bytes":exclusions,"callees":rows,"production_change":false,"performance_measurement":false,
        "limitation":"Historical exact-artifact call counts, not fresh timing. Hypothetical local extents exclude final temporary/inline layout and alignment effects, indirect targets and entry/TLS frames. No speedup is predicted."}))?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture()->(Function,Counts) {
        let f=Function{name:"counts".into(),frame_size:16,frame_align:8,registers:1,args:vec![],result:Slot{offset:0,size:0},
            code:vec![Op::Local{dst:0,offset:0},Op::Return]};
        let p=Counts{name:f.name.clone(),frame_size:16,registers:1,operations:f.code.iter().map(|op|format!("{op:?}")).collect(),
            interpreted:vec![1,2],jit_blocks:vec![3,0],jit_block_ends:vec![2,0],jit_tree_blocks:vec![4,0],jit_tree_block_ends:vec![1,0]};(f,p)
    }
    #[test] fn three_paths_and_identity_range_overflow_guards() {
        let (f,p)=fixture();assert_eq!(frequencies(&f,&p).unwrap(),[8,5]);
        let (_,mut p)=fixture();p.operations[0]="different".into();assert!(frequencies(&f,&p).is_err());
        let (_,mut p)=fixture();p.jit_tree_block_ends[0]=3;assert!(frequencies(&f,&p).is_err());
        let (_,mut p)=fixture();p.interpreted[0]=u64::MAX;assert!(frequencies(&f,&p).is_err());
        let (_,mut p)=fixture();p.jit_blocks.pop();assert!(frequencies(&f,&p).is_err());
    }
    #[test] fn inventory_dedicated_and_shared_ranges_are_checked() {
        let (f,_)=fixture();let slot=Storage{local:0,size:8,align:8,original_offset:0,hypothetical_offset:0,exclusion:None,eligible:true};
        let row=Inventory{id:0,name:f.name.clone(),old_local_extent:16,additional_bytes_saved:8,hypothetical_local_extent:Some(8),
            decline:None,production_change:false,baseline_slots_reconstructed:true,slots:vec![slot.clone(),Storage{local:1,original_offset:8,..slot}]};
        validate_inventory(&f,&row).unwrap();
        let mut wrong=row.clone();wrong.slots[1].eligible=false;wrong.slots[1].exclusion=Some("abi".into());assert!(validate_inventory(&f,&wrong).is_err());
        let mut wrong=row.clone();wrong.slots[1].hypothetical_offset=4;assert!(validate_inventory(&f,&wrong).is_err());
        let mut wrong=row.clone();wrong.decline=Some("bound".into());assert!(validate_inventory(&f,&wrong).is_err());
        let mut wrong=row;wrong.additional_bytes_saved=9;assert!(validate_inventory(&f,&wrong).is_err());
    }
}
