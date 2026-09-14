//! Reconstruct the final state of interleaved, incrementally patched fragments.
use super::*;

impl<'a> Jit<'a> {
    pub(super) fn validate_demand_mapping(&self, id: usize, publications: &[demand::Publication]) -> Result<(), String> {
        let entries = &self.blocks[id];
        let table = self.resumable.as_ref().ok_or("operation map demand table missing")?.published(id);
        if entries.len() != self.program.functions[id].code.len() || table.len() != entries.len() + 1
            || table.last() != Some(&0) {
            return Err("operation map invalid demand table extent".into());
        }
        let mut seen = vec![false; entries.len()];
        for p in publications {
            if p.pc >= seen.len() || seen[p.pc] || entries[p.pc].is_none() {
                return Err("operation map repeated or missing demand publication".into());
            }
            seen[p.pc] = true;
        }
        for (pc, entry) in entries.iter().enumerate() {
            if seen[pc] != entry.is_some() || seen[pc] != (table[pc] != 0)
                || seen[pc] != self.demand.as_ref().unwrap().internal(id, pc).is_some() {
                return Err("operation map incomplete demand entry coverage".into());
            }
        }
        Ok(())
    }

    pub(super) fn reconstruct_demand_mapping(&self, id: usize, p: &demand::Publication,
        end: usize, assertions: usize, collector: &mut Collector,
    ) -> Result<CompiledFunction<'a>, String> {
        if end.checked_sub(p.offset) != Some(p.bytes) || p.assertion_base != assertions {
            return Err("operation map demand publication extent or assertion base mismatch".into());
        }
        let state = self.demand.as_ref().ok_or("operation map missing demand owner")?;
        let plan = state.plan(id).ok_or("operation map missing retained demand plan")?;
        let mut staged = self.emit_analyzed_function(&self.program.functions[id], p.bytes / 4,
            assertions, Some(collector), plan, Some(p.pc))
            .map_err(|e| format!("operation map demand reconstruction: {e:?}"))?
            .ok_or("operation map demand reconstruction declined")?;
        if staged.selected != Some(p.pc) || staged.internal_entries.len() != 1
            || staged.entries.len() != 1 || staged.resumes.len() != 1
            || staged.assertions.len() != p.assertions {
            return Err("operation map demand reconstruction metadata mismatch".into());
        }
        let internal = staged.internal_entries[0].ok_or("operation map missing demand internal entry")?;
        if internal >= staged.words.len() || state.internal(id, p.pc) != Some(p.offset / 4 + internal) {
            return Err("operation map demand internal entry mismatch".into());
        }
        // Resolve only emitter-declared same-function branches. Unpublished
        // successors keep their original local fallback, including refusals.
        for &(at, successor, fallback) in &staged.region_links {
            let local = if successor == p.pc { internal } else { fallback };
            if at >= staged.words.len() || local >= staged.words.len() {
                return Err("operation map demand declaration outside fragment".into());
            }
            let jump = |at, target| branch_displacement(at, target, 26, CodegenLimit::Jump)
                .map(|delta| 0x14000000 | delta)
                .map_err(|_| "operation map demand branch displacement overflow");
            if staged.words[at] != jump(at, local)? {
                return Err("operation map demand declared fallback mismatch".into());
            }
            let target = state.internal(id, successor).unwrap_or(p.offset / 4 + fallback);
            if target >= self.bytes / 4 { return Err("operation map demand target outside arena".into()); }
            staged.words[at] = jump(p.offset / 4 + at, target)?;
        }
        Ok(staged)
    }
}
