//! Immutable whole-function inputs to ordinary native emission.
//! Region bounds and guarded ranges are computed once in source order.
use super::*;

#[cfg(test)]
mod storage;
// The pool is qualified before the demand publisher begins using it.
#[allow(dead_code)]
pub(super) mod retained;

pub(super) struct FunctionAnalysis {
    pub reads: Vec<Option<(usize, usize)>>,
    pub values: Option<values::Allocation>,
    pub fills: Vec<(usize, LocalFill)>,
    pub slots: Vec<(usize, Vec<Option<usize>>)>,
    pub regions: Vec<Region>,
}

pub(super) struct Region {
    pub start: usize,
    // An empty native body denotes one unsupported operation or transition.
    pub end: usize,
    pub range: Option<Box<range_groups::Plan>>,
}

pub(super) fn hint<T>(items: &[(usize, T)], pc: usize) -> Option<&T> {
    items.binary_search_by_key(&pc, |(key, _)| *key).ok().map(|i| &items[i].1)
}

impl FunctionAnalysis {
    // Charge requested owned buffer capacity and inline payload, not allocator
    // rounding, transient analysis or the full cfg(test) diagnostic oracle.
    fn retained_bytes(&self) -> Option<usize> {
        fn buffer<T>(v: &Vec<T>) -> Option<usize> { v.capacity().checked_mul(std::mem::size_of::<T>()) }
        let mut bytes = std::mem::size_of::<Self>();
        for size in [buffer(&self.reads), buffer(&self.fills), buffer(&self.slots), buffer(&self.regions)] {
            bytes = bytes.checked_add(size?)?;
        }
        for (_, hints) in &self.slots { bytes = bytes.checked_add(buffer(hints)?)?; }
        for region in &self.regions {
            if let Some(plan) = &region.range {
                bytes = bytes.checked_add(std::mem::size_of::<range_groups::Plan>())?.checked_add(buffer(&plan.sites)?)?;
            }
        }
        if let Some(values) = &self.values { bytes = bytes.checked_add(values.retained_buffer_bytes()?)?; }
        Some(bytes)
    }
}

impl Jit<'_> {
    pub(super) fn analyze_function(&self, f: &Function) -> FunctionAnalysis {
        let resumable = self.resumable.is_some();
        let reads = read_registers(f);
        let values = self.persistent_registers.then(|| values::analyze(f)).flatten();
        let fills = local_fills(f);
        let slots = if resumable { call_slots::collect(f, self.program) } else { std::collections::BTreeMap::new() };
        #[cfg(test)]
        let slots = if self.disable_call_slot_hints { std::collections::BTreeMap::new() } else { slots };
        let native = |pc: usize| supported(&f.code[pc]) || fills.contains_key(&pc)
            || (resumable && transfers::supported(&f.code[pc]));
        let mut starts = vec![false; f.code.len()];
        starts[0] = true;
        for (pc, op) in f.code.iter().enumerate() {
            match op {
                Op::Jump { target } => starts[*target] = true,
                Op::Switch {
                    cases, otherwise, ..
                } => {
                    starts[*otherwise] = true;
                    for (_, target) in cases {
                        starts[*target] = true;
                    }
                }
                _ => {}
            }
            if (!native(pc) || branch(op)) && pc + 1 < f.code.len() {
                starts[pc + 1] = true;
            }
        }
        let mut regions = vec![];
        let mut pc = 0;
        let mut range_work = 4_000_000;
        while pc < f.code.len() {
            let start = pc;
            // Keep the same leader and branch-range limits as eager emission.
            while pc < f.code.len() && pc - start < 1024
                && (pc == start || !starts[pc]) && native(pc) {
                pc += 1;
            }
            let range = if resumable && pc > start {
                range_groups::runtime_plan(f, start, pc, &mut range_work).map(Box::new)
            } else { None };
            regions.push(Region { start, end: pc, range });
            if pc == start { pc += 1; }
        }
        FunctionAnalysis { reads, values, fills: fills.into_iter().collect(), slots: slots.into_iter().collect(), regions }
    }
}
