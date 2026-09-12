//! Experimental child of byte_writes. Relocation is validated before mutation.
use super::*;

fn end(slot: Slot) -> Option<usize> { slot.offset.checked_add(slot.size) }
fn same(a: Slot, b: Slot) -> bool { a.offset == b.offset && a.size == b.size }

struct Relocation {
    locals: Vec<(usize, usize)>, // bytecode PC -> replacement offset
    args: Vec<Slot>,
    result: Slot,
    frame_size: usize,
}

fn prepare(f: &Function, old: &[Slot], new: &[Slot], shapes: &[(usize,usize)], eligible: &[bool],
           extent: usize, proposed: usize, abi_count: usize, origins: &BTreeMap<Reg,usize>) -> Option<Relocation> {
    let n = old.len();
    if n == 0 || n > MAX_LOCALS || new.len()!=n || shapes.len()!=n || eligible.len()!=n ||
        abi_count==0 || abi_count>n || !f.frame_align.is_power_of_two() ||
        extent>f.frame_size || proposed>=extent || !same(f.result, old[0]) { return None; }
    let delta = (extent-proposed) & !(f.frame_align-1);
    if delta==0 { return None; }
    let frame_size = f.frame_size.checked_sub(delta)?;
    // Independent physical-range certificate. Only identical eligible shapes
    // may overlap; all dedicated storage (including ABI) remains disjoint.
    let mut ranges = BTreeMap::<(usize,usize),(usize,bool)>::new();
    for i in 0..n {
        let (size,align) = shapes[i];
        if !align.is_power_of_two() || align>f.frame_align || old[i].size!=size || new[i].size!=size ||
            old[i].offset%align!=0 || new[i].offset%align!=0 || end(old[i])?>extent || end(new[i])?>proposed ||
            (i<abi_count && eligible[i]) { return None; }
        if size!=0 {
            let key=(new[i].offset,size);
            if let Some(&(a,e))=ranges.get(&key) {
                if a!=align || !e || !eligible[i] { return None; }
            } else { ranges.insert(key,(align,eligible[i])); }
        }
    }
    let mut previous_end=0;
    for (&(offset,size),_) in &ranges {
        if offset<previous_end { return None; }
        previous_end=offset.checked_add(size)?;
    }
    let trailing = |slot:Slot| -> Option<Slot> {
        if slot.offset<extent || end(slot)?>f.frame_size { return None; }
        let moved=Slot {offset:slot.offset.checked_sub(delta)?,size:slot.size};
        if moved.offset<proposed || end(moved)?>frame_size { return None; }
        Some(moved)
    };
    let mut args=Vec::with_capacity(f.args.len());
    for &arg in &f.args {
        // Zero-byte formal arguments are elided by the retained lowering.
        // Do not guess a containing origin for a malformed extra zero slot.
        if arg.size==0 { return None; }
        if arg.offset>=extent { args.push(trailing(arg)?); continue; }
        let mut found=None;
        for i in 1..abi_count {
            if old[i].size!=0 && arg.offset>=old[i].offset && end(arg)?<=end(old[i])? {
                if found.is_some() { return None; }
                let offset=new[i].offset.checked_add(arg.offset-old[i].offset)?;
                found=Some(Slot{offset,size:arg.size});
            }
        }
        args.push(found?);
    }
    let mut locals=vec![];
    let mut seen=BTreeSet::new();
    for (pc,op) in f.code.iter().enumerate() {
        if let Op::Local{dst,offset}=op {
            if *dst as usize>=f.registers || !seen.insert(*dst) { return None; }
            let offset=if let Some(&i)=origins.get(dst) {
                if i>=n || old[i].offset!=*offset { return None; }
                new[i].offset
            } else {
                trailing(Slot{offset:*offset,size:0})?.offset
            };
            locals.push((pc,offset));
        }
    }
    Some(Relocation{locals,args,result:new[0],frame_size})
}

fn apply(f: &mut Function, r: Relocation) {
    for (pc,offset) in r.locals {
        let Op::Local{offset:at,..}=&mut f.code[pc] else { unreachable!("validated relocation") };
        *at=offset;
    }
    f.args=r.args; f.result=r.result; f.frame_size=r.frame_size;
}

pub(super) fn transform(observations: Vec<Observation>, program: &mut Program) {
    let start=std::time::Instant::now();
    let (mut functions,mut saved,mut capture_nanos)=(0usize,0usize,0u128);
    let mut declines=BTreeMap::<&str,usize>::new();
    for mut o in observations {
        capture_nanos+=o.capture_nanos;
        let f=&program.functions[o.id];
        assert_eq!(f.name,o.name,"function identity differs at relocation");
        if let Some(reason)=o.decline { *declines.entry(reason).or_default()+=1; continue; }
        assert!(o.baseline,"missing original scalar-layout certificate");
        for w in &o.writes {
            if !w.coverage.complete(o.slots[w.local],program) {
                o.events[w.block][w.event].reads.insert(w.local);
            }
        }
        let mut eligible=vec![];
        let Some((slots,proposed))=plan_with_eligibility(&o.shapes,o.reasons.iter().map(Option::is_none).collect(),
            o.events,&o.successors,Some(&mut eligible)) else {
                *declines.entry("planner_bound").or_default()+=1; continue;
            };
        if proposed>=o.extent || o.extent-proposed<f.frame_align { continue; }
        let Some(r)=prepare(f,&o.slots,&slots,&o.shapes,&eligible,o.extent,proposed,o.abi_count,&o.origins) else {
            *declines.entry("relocation_certificate").or_default()+=1; continue;
        };
        saved+=f.frame_size-r.frame_size; functions+=1;
        apply(&mut program.functions[o.id],r);
    }
    eprintln!("rust-interp-aggregate-frames: {}",serde_json::json!({"functions":functions,"static_bytes_saved":saved,
        "declines":declines,"finalize_seconds":start.elapsed().as_secs_f64(),"capture_seconds":capture_nanos as f64/1e9,
        "initialization_unchanged":true}));
}

#[cfg(test)]
#[path="aggregate_relocation_tests.rs"]
mod tests;
