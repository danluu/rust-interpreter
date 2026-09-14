//! Immutable whole-function inputs to ordinary native emission.
//! Region bounds and guarded ranges are computed once in source order.
use super::*;

pub(super) struct FunctionAnalysis {
    pub reads: Vec<Option<(usize, usize)>>,
    pub values: Option<values::Allocation>,
    pub fills: BTreeMap<usize, LocalFill>,
    pub slots: BTreeMap<usize, Vec<Option<usize>>>,
    pub regions: Vec<Region>,
}

pub(super) struct Region {
    pub start: usize,
    // An empty native body denotes one unsupported operation or transition.
    pub end: usize,
    pub range: Option<Box<range_groups::Plan>>,
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
        FunctionAnalysis { reads, values, fills, slots, regions }
    }
}
