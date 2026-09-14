//! Immutable whole-function inputs to ordinary native emission.
//! This refactor retains eager emission and does not cache or publish plans.
use super::*;

pub(super) struct FunctionAnalysis {
    pub reads: Vec<Option<(usize, usize)>>,
    pub values: Option<values::Allocation>,
    pub fills: BTreeMap<usize, LocalFill>,
    pub slots: BTreeMap<usize, Vec<Option<usize>>>,
    pub starts: Vec<bool>,
}

impl FunctionAnalysis {
    pub fn native(&self, f: &Function, pc: usize, resumable: bool) -> bool {
        supported(&f.code[pc]) || self.fills.contains_key(&pc)
            || (resumable && transfers::supported(&f.code[pc]))
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
        FunctionAnalysis { reads, values, fills, slots, starts }
    }
}
