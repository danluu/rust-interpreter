//! Offline lifetime allocation. No VM or exporter path applies this mapping.
use crate::{Function, Op, Program, Reg};
use std::collections::BTreeSet;

const MAX_WORK: usize = 32_000_000;

struct Plan {
    mapping: Vec<Reg>,
    slots: usize,
    referenced: usize,
    baseline_resident: Vec<Reg>,
}

fn plan(f: &Function, limit: usize) -> Option<Plan> {
    let (live, ranked) = super::values::ranked(f, limit)?;
    let mut intervals = vec![None::<(usize, usize)>; f.registers];
    let mut work = 0usize;
    for (pc, op) in f.code.iter().enumerate() {
        let mut touch = |r: Reg| {
            let range = &mut intervals[r as usize];
            if let Some((_, end)) = range { *end = pc; } else { *range = Some((pc, pc)); }
        };
        // Liveness includes loops, joins, unreachable blocks and initial-zero
        // reads. All live identities must span this point even without a use.
        for (word, &bits) in live.bits[pc * live.stride..(pc + 1) * live.stride].iter().enumerate() {
            work = work.checked_add(1 + bits.count_ones() as usize)?;
            if work > limit { return None; }
            let mut remaining = bits;
            while remaining != 0 {
                touch((word * 64 + remaining.trailing_zeros() as usize) as Reg);
                remaining &= remaining - 1;
            }
        }
        let mut accesses = Vec::new();
        crate::registers::visit_registers(op, |r| accesses.push(r), |_| {});
        crate::registers::visit_registers(op, |_| {}, |r| accesses.push(r));
        work = work.checked_add(accesses.len())?;
        if work > limit { return None; }
        // Dead writes and every output participate. Closed intervals forbid
        // new input/output or multi-output aliases within an instruction.
        for r in accesses { touch(r); }
    }
    let mut ordered: Vec<_> = intervals.iter().enumerate()
        .filter_map(|(r, range)| range.map(|(start, end)| (start, end, r))).collect();
    ordered.sort_unstable();
    let referenced = ordered.len();
    let mut mapping = vec![Reg::MAX; f.registers];
    let mut active = BTreeSet::new();
    let mut free = BTreeSet::new();
    let mut slots = 0;
    for &(start, end, r) in &ordered {
        while active.first().is_some_and(|&(until, _)| until < start) {
            let (_, slot) = active.pop_first()?;
            free.insert(slot);
        }
        let slot = free.pop_first().unwrap_or_else(|| { let slot = slots; slots += 1; slot });
        mapping[r] = slot as Reg;
        active.insert((end, slot));
    }
    // Certify the allocator independently of its active/free data structures.
    // Every interval assigned to one slot must be strictly disjoint; this also
    // protects initial zeroes from unrelated writes before their first read.
    let mut previous_end = vec![None; slots];
    for &(start, end, r) in &ordered {
        let slot = mapping[r] as usize;
        if previous_end[slot].is_some_and(|previous| previous >= start) { return None; }
        previous_end[slot] = Some(end);
    }
    Some(Plan { mapping, slots, referenced,
        baseline_resident: ranked.into_iter().take(3).map(|(_, r)| r).collect() })
}

fn remap(f: &Function, plan: &Plan) -> Function {
    let mut result = f.clone();
    result.registers = plan.slots;
    let r = |value: &mut Reg| {
        *value = plan.mapping[*value as usize];
        assert_ne!(*value, Reg::MAX, "referenced register absent from lifetime plan");
    };
    for op in &mut result.code {
        // Exhaustive typed operands. Branch targets, sizes and function IDs
        // are untouched. Calls' destinations are addresses, not new values.
        match op {
            Op::Imm { dst, .. } | Op::Local { dst, .. } => r(dst),
            Op::Load { dst, address, .. } => { r(dst); r(address); }
            Op::Store { address, src, .. } => { r(address); r(src); }
            Op::Copy { dst, src, .. } => { r(dst); r(src); }
            Op::Binary { dst, overflow, a, b, .. } => { r(dst); r(overflow); r(a); r(b); }
            Op::Unary { dst, src, .. } | Op::Cast { dst, src, .. }
            | Op::FloatUnary { dst, src, .. } | Op::FloatConvert { dst, src, .. } => { r(dst); r(src); }
            Op::Select { dst, condition, yes, no } => { r(dst); r(condition); r(yes); r(no); }
            Op::Switch { value, .. } | Op::Assert { value, .. } => r(value),
            Op::Call { args, destination, .. } => { for arg in args { r(arg); } r(destination); }
            Op::CallIndirect { callee, args, destination, .. } => { r(callee); for arg in args { r(arg); } r(destination); }
            Op::CopyDynamic { dst, src, size } => { r(dst); r(src); r(size); }
            Op::CompareBytes { dst, left, right, size } => { r(dst); r(left); r(right); r(size); }
            Op::Allocate { dst, size, align, .. } => { r(dst); r(size); r(align); }
            Op::Deallocate { pointer, size, align } => { r(pointer); r(size); r(align); }
            Op::Reallocate { dst, pointer, old_size, align, new_size } => { r(dst); r(pointer); r(old_size); r(align); r(new_size); }
            Op::FillBytes { address, value, size } => { r(address); r(value); r(size); }
            Op::FloatBinary { dst, a, b, .. } => { r(dst); r(a); r(b); }
            Op::RandomBytes { dst, address, size } => { r(dst); r(address); r(size); }
            Op::DescriptorOpen { dst, path, flags, mode, errno } => {
                for value in [dst, path, flags, errno] { r(value); } if let Some(mode)=mode { r(mode); }
            }
            Op::DescriptorWrite { dst, descriptor, address, size, errno } => {
                for value in [dst, descriptor, address, size, errno] { r(value); }
            }
            Op::DescriptorClose { dst, descriptor, errno } | Op::DescriptorGetFd { dst, descriptor, errno } => {
                for value in [dst, descriptor, errno] { r(value); }
            }
            Op::EnvironmentGet { dst, name } => { r(dst); r(name); }
            Op::CpuFeatureQuery { dst, name, output, output_len, new_data, new_len } => {
                for value in [dst, name, output, output_len, new_data, new_len] { r(value); }
            }
            Op::CAllocate { dst, count, size, errno, .. } => { for value in [dst, count, size, errno] { r(value); } }
            Op::CReallocate { dst, pointer, size, errno } => { for value in [dst, pointer, size, errno] { r(value); } }
            Op::CAlignedAllocate { dst, output, align, size } => { for value in [dst, output, align, size] { r(value); } }
            Op::CDeallocate { pointer } => r(pointer),
            Op::RegisterTlsDestructor { callback, argument } => { r(callback); r(argument); }
            Op::Jump { .. } | Op::Return | Op::Trap { .. } | Op::ResetThreadLocals => {}
        }
    }
    result
}

pub(super) fn census(program: &Program, profile_bytes: Option<&[u8]>) -> Result<serde_json::Value, String> {
    crate::validate(program)?;
    let profile = profile_bytes.map(|bytes| super::register_width_profile::parse(program, bytes)).transpose()?;
    let mut rows = Vec::new();
    let mut totals = [0u64; 6];
    let mut declined = 0;
    let add = |a: &mut u64, b| -> Result<(), String> { *a = a.checked_add(b).ok_or("lifetime census counter overflow")?; Ok(()) };
    for (id, f) in program.functions.iter().enumerate() {
        let Some(plan) = plan(f, MAX_WORK) else {
            declined += 1;
            rows.push(serde_json::json!({"function":id,"old_slots":f.registers,"declined":true}));
            continue;
        };
        let mapped = remap(f, &plan);
        let assigned = super::values::analyze(&mapped);
        let native = profile.as_ref().map(|p| p.functions[id].native_counts(f)).transpose()?;
        let mut counts = [0u64; 3];
        for (pc, op) in f.code.iter().enumerate() {
            let weight = native.as_ref().map_or(1, |counts| counts[pc]);
            let mut accesses = [0u64; 3];
            crate::registers::visit_registers(op, |r| {
                accesses[0] += 1;
                accesses[1] += u64::from(plan.baseline_resident.contains(&r));
                accesses[2] += u64::from(assigned.as_ref().is_some_and(|a| a.registers.contains(&plan.mapping[r as usize])));
            }, |_| {});
            for (count, n) in counts.iter_mut().zip(accesses) {
                add(count, weight.checked_mul(n).ok_or("lifetime census counter overflow")?)?;
            }
        }
        for (total, value) in totals.iter_mut().zip([f.registers as u64, plan.referenced as u64, plan.slots as u64, counts[0], counts[1], counts[2]]) {
            add(total, value)?;
        }
        rows.push(serde_json::json!({"function":id,"old_slots":f.registers,"referenced_slots":plan.referenced,
            "allocated_slots":plan.slots,"declined":false,"new_residency_declined":assigned.is_none(),
            "operand_reads":counts[0],"baseline_assigned_reads":counts[1],"allocated_assigned_reads":counts[2],
            "baseline_resident":plan.baseline_resident,"allocated_resident":assigned.as_ref().map(|a| &a.registers)}));
    }
    Ok(serde_json::json!({"schema_version":1,"functions":rows,"declined_functions":declined,
        "old_slots_in_admitted_functions":totals[0],"referenced_slots":totals[1],"allocated_slots":totals[2],
        "operand_reads":totals[3],"baseline_assigned_reads":totals[4],"allocated_assigned_reads":totals[5],
        "profile_weighted":profile.is_some(),"performance_measurement":false,
        "scope":"Typed lifetime allocation census; original native operation counters weight reads. Residency counts exclude transfer/setup costs and declined functions; they do not predict machine traffic or elapsed time. No guest execution or artifact publication."}))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Binary, Slot};
    fn function(code: Vec<Op>, registers: usize) -> Function {
        Function { name:"lifetimes".into(),frame_size:16,frame_align:16,registers,
            args:vec![],result:Slot {offset:0,size:0},code }
    }
    #[test]
    fn disjoint_values_share_storage_but_live_addresses_do_not() {
        let f = function(vec![Op::Local {dst:0,offset:0},Op::Imm {dst:4,value:5},
            Op::Store {address:0,src:4,size:8},Op::Imm {dst:5,value:6},
            Op::Store {address:0,src:5,size:8},Op::Return], 8);
        let p = plan(&f, MAX_WORK).unwrap();
        assert_eq!((p.slots,p.referenced),(2,3));
        assert_eq!(p.mapping[4],p.mapping[5]);assert_ne!(p.mapping[0],p.mapping[4]);
        assert_eq!(remap(&f,&p).code.len(),f.code.len());
    }
    #[test]
    fn initial_zeroes_and_dead_writes_interfere() {
        let f = function(vec![Op::Imm {dst:0,value:99},Op::Assert {value:1,expected:false,message:"zero".into()},Op::Return],2);
        let p = plan(&f,MAX_WORK).unwrap();assert_ne!(p.mapping[0],p.mapping[1]);
    }
    #[test]
    fn backedges_keep_values_live_across_the_numerical_gap() {
        let f = function(vec![Op::Jump {target:3},Op::Assert {value:0,expected:true,message:"loop".into()},
            Op::Return,Op::Imm {dst:0,value:1},Op::Imm {dst:1,value:9},Op::Jump {target:1}],2);
        let p = plan(&f,MAX_WORK).unwrap();assert_ne!(p.mapping[0],p.mapping[1]);
    }
    #[test]
    fn joins_and_unreachable_uses_participate() {
        let f = function(vec![Op::Switch {value:0,cases:vec![(0,3)],otherwise:1},Op::Imm {dst:1,value:4},
            Op::Jump {target:4},Op::Imm {dst:2,value:5},Op::Assert {value:1,expected:false,message:"join".into()},
            Op::Return,Op::Store {address:1,src:2,size:8},Op::Return],3);
        let p = plan(&f,MAX_WORK).unwrap();assert_ne!(p.mapping[1],p.mapping[2]);
    }
    #[test]
    fn inputs_and_distinct_outputs_never_gain_aliases() {
        let f = function(vec![Op::Binary {dst:1,overflow:2,op:Binary::Add,a:0,b:0,bits:128,signed:false},Op::Return],3);
        let p = plan(&f,MAX_WORK).unwrap();assert_eq!(p.slots,3);
        let f = function(vec![Op::Binary {dst:1,overflow:1,op:Binary::Add,a:0,b:0,bits:128,signed:false},Op::Return],2);
        let p = plan(&f,MAX_WORK).unwrap();
        assert!(matches!(remap(&f,&p).code[0],Op::Binary {dst,overflow,..} if dst==overflow));
    }
    #[test]
    fn calls_read_addresses_and_bounds_decline_conservatively() {
        let f = function(vec![Op::Imm {dst:0,value:3},Op::Call {function:0,args:vec![0],destination:1},Op::Return],2);
        let p = plan(&f,MAX_WORK).unwrap();assert_ne!(p.mapping[0],p.mapping[1]);
        assert!(plan(&f,0).is_none());
        assert!(plan(&function(vec![Op::Imm {dst:5,value:0}],1),MAX_WORK).is_none());
        assert!(plan(&function(vec![Op::Return],65_537),MAX_WORK).is_none());
    }
}
