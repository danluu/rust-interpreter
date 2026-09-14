//! Reuse only values still available in the current native region's fact table.
use super::*;

const MAX_VALUES: usize = 16;

pub(super) struct Value {
    offset: usize,
    size: usize,
    source: Reg,
}

impl Assembler<'_> {
    pub(super) fn local_range(&self, address: Reg, size: usize) -> Option<usize> {
        match self.facts.get(&address) {
            Some(Fact::Local(offset)) if offset.checked_add(size).is_some_and(|end| end <= self.frame_size) => Some(*offset),
            _ => None,
        }
    }

    pub(super) fn forget_local_register(&mut self, register: Reg) {
        self.local_values.retain(|value| value.source != register);
    }

    pub(super) fn invalidate_local_memory(&mut self, offset: Option<usize>, size: usize) {
        self.scratch_values.invalidate(offset,size);
        #[cfg(test)]
        self.scratch.invalidate(offset, size);
        if size == 0 { return; }
        let Some(offset) = offset else { self.local_values.clear(); return; };
        let end = offset.checked_add(size).expect("proved local extent");
        self.local_values.retain(|value| value.offset >= end || offset >= value.offset + value.size);
    }

    pub(super) fn local_value(&self, offset: Option<usize>, size: usize) -> Option<(Reg, Fact)> {
        if ![1,2,4,8].contains(&size) { return None; }
        let offset = offset?;
        let value = self.local_values.iter().find(|value| value.offset == offset && value.size == size)?;
        // Eviction may discard a dead value without spilling it. Never fall
        // back to reading that register's array slot for a forwarded access.
        self.facts.get(&value.source).copied().map(|fact| (value.source, fact))
    }

    pub(super) fn remember_local_memory(&mut self, offset: Option<usize>, size: usize, source: Reg) {
        if ![1,2,4,8].contains(&size) || !self.facts.contains_key(&source) { return; }
        let Some(offset) = offset else { return; };
        self.local_values.retain(|value| value.offset != offset || value.size != size);
        if self.local_values.len() == MAX_VALUES { self.local_values.remove(0); }
        self.local_values.push(Value { offset, size, source });
    }

    pub(super) fn forward_local_value(&mut self, fact: Fact, size: usize, _kind: &'static str) {
        #[cfg(test)]
        let previous_part = std::mem::replace(&mut self.memory_parts.part, "forwarded_value");
        // This extra use must not alter the original cache replacement order.
        // The owner is still available; no new register-array read is needed.
        let recent = self.cache_recent;
        self.materialize(9, fact, false);
        self.cache_recent = recent;
        self.mask(9, (size * 8) as u8);
        #[cfg(test)]
        self.observe_forwarded_fact(fact, _kind);
        #[cfg(test)]
        { self.memory_parts.part = previous_part; }
    }

    #[cfg(test)]
    pub(super) fn observe_forwarded_fact(&mut self, fact: Fact, opcode: &'static str) {
        self.local_forwarding.push((self.current_pc, opcode));
        let kind = match fact { Fact::Imm(_) => "Imm", Fact::Local(_) => "Local",
            Fact::Cached {..} => "Cached", Fact::Physical {..} => "Physical" };
        self.local_fact_events.push((self.current_pc, opcode, kind));
    }

    pub(super) fn preserve_guarded_local_write(&mut self, local: Option<usize>, reg: Reg, size: usize) -> bool {
        #[cfg(test)]
        if !self.observe_guarded_local_retention { return false; }
        if local.is_some() || size == 0 { return false; }
        // Immutable query: no synthetic live-in use may be added after the write.
        let proven = self.guarded_range.as_ref().is_some_and(|plan| plan.frame_disjoint
            && plan.displacement(self.current_pc, reg, size, true).is_some());
        #[cfg(test)]
        if proven {
            self.retained_local_writes.push((self.current_pc, reg, size, self.local_values.len()));
        }
        proven
    }

    fn scalar_local_memory_immediate(&self, reg: Reg, size: usize) -> Option<u32> {
        if [1, 2, 4, 8, 16].contains(&size) {
            if let Some(offset) = self.local_range(reg, size) {
                let scale = size.min(8);
                let immediate = offset / scale;
                if offset % scale == 0 && immediate < 4096 - usize::from(size == 16) {
                    return Some(immediate as u32);
                }
            }
        }
        None
    }
    pub(super) fn scalar_copy(&mut self, dst: Reg, src: Reg, size: usize, forwarded: Option<Fact>) {
        debug_assert!([1, 2, 4, 8, 16].contains(&size));
        if let Some(value) = forwarded {
            // Preserve destination validation before materializing the captured
            // value, including the original cache replacement order.
            let immediate = memory_access!(self, "destination", self.memory_address(12, dst, size, true));
            self.forward_local_value(value, size, "Copy");
            #[cfg(test)]
            if self.scratch.is_extended() {
                self.scratch.capture(self.current_pc,self.local_range(src,size),size,"CopySource");
            }
            self.store_mem_at(9, 31, 12, size, immediate);
            return;
        }
        let high = if size <= 8 { 31 } else { 10 };
        let (source, destination_base, destination) = match (
            self.scalar_local_memory_immediate(src, size), self.scalar_local_memory_immediate(dst, size),
        ) {
            (Some(source), Some(destination)) => {
                // Both complete ranges are already proven in the same active
                // frame. Share its host base; only the memory displacements
                // differ. Neither load overwrites this base.
                memory_access!(self, "both", memory_part!(self, "shared_frame_address", self.three(0x8b000000, 11, 2, 1)));
                (source, 11, destination)
            }
            _ => {
                // Preserve source-before-destination checks and validate both
                // entire ranges before touching any bytes.
                let source = memory_access!(self, "source", self.memory_address(11, src, size, false));
                let destination = memory_access!(self, "destination", self.memory_address(12, dst, size, true));
                (source, 12, destination)
            }
        };
        // Even a sixteen-byte overlapping copy loads both words before its
        // first store. Narrow copies never consume or define the high scratch.
        #[cfg(test)]
        if !self.scratch.is_extended() || !self.scratch_values.contains(self.local_range(src,size),size) {
            self.scratch.copy_load(self.current_pc,self.local_range(src,size),size);
        }
        if !self.scratch_values.contains(self.local_range(src,size),size) {
            self.load_mem_at(9, high, 11, size, source);
        }
        #[cfg(test)]
        if self.scratch.is_extended() {
            // Record the pre-write source. The enclosing Copy's typed write
            // invalidation removes it if the destination overlaps these bytes.
            self.scratch.capture(self.current_pc,self.local_range(src,size),size,"CopySource");
        }
        self.store_mem_at(9, high, destination_base, size, destination);
    }
    pub(super) fn review_local_memory_effect(&mut self, op: &Op) {
        // Store/Copy and fused local_fill update exact ranges in their paths.
        // Other effects are conservative, even if currently interpreted. A new
        // opcode requires an explicit review instead of inheriting a wildcard.
        match op {
            Op::Imm {..} | Op::Local {..} | Op::Load {..} | Op::Store {..} | Op::Copy {..}
            | Op::Binary {..} | Op::Unary {..} | Op::Cast {..} | Op::Select {..}
            | Op::Jump {..} | Op::Switch {..} | Op::Assert {..} | Op::Return | Op::Trap {..}
            | Op::CompareBytes {..} | Op::FloatBinary {..} | Op::FloatUnary {..} | Op::FloatConvert {..} => {},
            Op::Call {..} | Op::CallIndirect {..} | Op::CopyDynamic {..} | Op::FillBytes {..}
            | Op::Allocate {..} | Op::Deallocate {..} | Op::Reallocate {..} | Op::RandomBytes {..}
            | Op::DescriptorOpen {..} | Op::DescriptorWrite {..} | Op::DescriptorClose {..} | Op::DescriptorGetFd {..} | Op::CurrentDirectory {..} | Op::DescriptorStat {..}
            | Op::CpuFeatureQuery {..} | Op::EnvironmentGet {..} | Op::CAllocate {..} | Op::CDeallocate {..}
            | Op::CReallocate {..} | Op::CAlignedAllocate {..} | Op::RegisterTlsDestructor {..}
            | Op::ResetThreadLocals => {
                self.local_values.clear();
                self.scratch_values.invalidate(None,1);
                #[cfg(test)]
                self.scratch.invalidate(None, 1);
            },
        }
    }
}
