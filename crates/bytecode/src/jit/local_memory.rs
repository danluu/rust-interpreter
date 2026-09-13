//! Reuse only values still available in the current native region's fact table.
use super::*;

const MAX_VALUES: usize = 16;

#[cfg(test)]
#[path = "local_memory/transfer_tests.rs"]
mod transfer_tests;

#[cfg_attr(test, derive(Clone, Copy, Debug, PartialEq, Eq))]
pub(super) struct Value {
    offset: usize,
    size: usize,
    source: Reg,
}

#[cfg(test)]
#[derive(serde::Serialize)]
pub(super) struct TransferEvent {
    pc: usize,
    source: Reg,
    destination: Reg,
    width: usize,
    outcome: &'static str,
    retained: usize,
    transferred: usize,
    too_wide: usize,
}

#[cfg(test)]
pub(super) struct TransferSnapshot {
    source: Reg,
    destination: Reg,
    width: usize,
    before: Vec<Value>,
}

#[cfg(test)]
impl Assembler<'_> {
    pub(super) fn capture_local_transfer(&mut self, source: Reg, destination: Reg,
        width: usize, fact: Fact) -> Option<TransferSnapshot> {
        if !self.observe_local_transfer { return None; }
        let excluded = match fact {
            Fact::Imm(_) => Some("immediate-source"),
            Fact::Local(_) => Some("local-pointer-source"),
            Fact::Physical {..} => Some("physical-source"),
            Fact::Cached {..} if source == destination => Some("same-register"),
            Fact::Cached {..} if self.reads[destination as usize].is_none() => Some("dead-destination"),
            Fact::Cached {..} => None,
        };
        if let Some(outcome) = excluded {
            self.local_transfer_events.push(TransferEvent { pc:self.current_pc, source, destination,
                width, outcome, retained:0, transferred:0, too_wide:0 });
            return None;
        }
        assert!([1,2,4,8].contains(&width) && self.local_values.len() <= MAX_VALUES);
        Some(TransferSnapshot { source, destination, width, before:self.local_values.clone() })
    }

    pub(super) fn finish_local_transfer(&mut self, snapshot: Option<TransferSnapshot>) {
        let Some(TransferSnapshot {source, destination, width, before}) = snapshot else { return; };
        // put() may only remove existing metadata. No guest write occurs between
        // capture and this point. Preserve the exact order of every survivor.
        assert!(before.iter().filter(|v| self.local_values.contains(v)).eq(self.local_values.iter()));
        let available = self.facts.contains_key(&destination);
        let retained = before.iter().filter(|v| v.source == source && self.local_values.contains(v)).count();
        let missing: Vec<_> = before.iter().filter(|v| v.source == source && !self.local_values.contains(v)).collect();
        let too_wide = missing.iter().filter(|v| v.size > width).count();
        let transferred = if available { missing.len() - too_wide } else { 0 };
        if transferred != 0 {
            let survivors = std::mem::take(&mut self.local_values);
            self.local_values = before.into_iter().filter_map(|mut value| {
                if survivors.contains(&value) { Some(value) }
                else if value.source == source && value.size <= width {
                    value.source = destination;
                    Some(value)
                } else { None }
            }).collect();
            assert!(self.local_values.len() <= MAX_VALUES);
        }
        let outcome = if !available {"unavailable-destination"} else if transferred != 0 {"transferred"}
                      else if too_wide != 0 {"incompatible-width"} else {"source-survived"};
        self.local_transfer_events.push(TransferEvent {pc:self.current_pc, source, destination,
            width, outcome, retained, transferred, too_wide});
    }
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
        // This extra use must not alter the original cache replacement order.
        // The owner is still available; no new register-array read is needed.
        let recent = self.cache_recent;
        self.materialize(9, fact, false);
        self.cache_recent = recent;
        self.mask(9, (size * 8) as u8);
        #[cfg(test)]
        self.observe_forwarded_fact(fact, _kind);
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
            let immediate = self.memory_address(12, dst, size, true);
            self.forward_local_value(value, size, "Copy");
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
                self.three(0x8b000000, 11, 2, 1);
                (source, 11, destination)
            }
            _ => {
                // Preserve source-before-destination checks and validate both
                // entire ranges before touching any bytes.
                let source = self.memory_address(11, src, size, false);
                let destination = self.memory_address(12, dst, size, true);
                (source, 12, destination)
            }
        };
        // Even a sixteen-byte overlapping copy loads both words before its
        // first store. Narrow copies never consume or define the high scratch.
        self.load_mem_at(9, high, 11, size, source);
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
            | Op::CpuFeatureQuery {..} | Op::EnvironmentGet {..} | Op::CAllocate {..} | Op::CDeallocate {..}
            | Op::CReallocate {..} | Op::CAlignedAllocate {..} | Op::RegisterTlsDestructor {..}
            | Op::ResetThreadLocals => self.local_values.clear(),
        }
    }
}
