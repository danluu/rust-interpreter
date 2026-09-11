//! VM boundary for experimental, completely prepared native call trees.
use crate::{ExecutionProfile, Limits, Memory, jit};

pub(crate) struct Context {
    // Every counter Vec is allocated once by ExecutionProfile::new and never
    // resized. This table lives only within the same exclusive VM execution.
    profile_table: Vec<*mut u64>,
    pub entries: u64,
    pub calls: u64,
    pub instructions: u64,
}
impl Context {
    pub fn new(profile: Option<&mut ExecutionProfile>) -> Self {
        Self { profile_table: profile.map_or_else(Vec::new, |p|
            p.functions.iter_mut().map(|f| f.jit_tree_blocks.as_mut_ptr()).collect()),
            entries: 0, calls: 0, instructions: 0 }
    }

    pub fn run<const PROFILE: bool>(&mut self, jit: &mut jit::Jit<'_>, function: usize,
        return_address: usize, base: usize, register_base: usize, caller_frames: usize,
        budget: u64, limits: &Limits, memory: &mut Memory, registers: &mut Vec<u128>,
        profile: &mut Option<&mut ExecutionProfile>,
    ) -> Result<Option<u64>, String> {
        let Some(plan) = jit.ensure_tree(function)? else { return Ok(None); };
        // These conservative guards are optimization declines, not guest
        // faults. Falling back preserves untaken paths and VM fault ordering.
        if budget < plan.instructions || caller_frames.checked_add(plan.depth).is_none_or(|n| n > limits.frames) {
            return Ok(None);
        }
        let Some(memory_end) = base.checked_add(plan.frame_span) else { return Ok(None); };
        let Some(register_end) = register_base.checked_add(plan.register_slots) else { return Ok(None); };
        let fixed = memory.heap.bytes.len().checked_add(memory.auxiliary_bytes);
        let working = register_end.checked_mul(16).and_then(|n| n.checked_add(memory_end))
            .and_then(|n| n.checked_add(fixed?));
        if working.is_none_or(|n| n > limits.memory) { return Ok(None); }
        // Native code cannot allocate or grow backing Vecs. Prepare every
        // initialized element now without publishing speculative guest bytes.
        if memory.bytes.prepare(memory_end).is_err() { return Ok(None); }
        if register_end > registers.len() {
            if registers.try_reserve(register_end - registers.len()).is_err() { return Ok(None); }
            registers.resize(register_end, 0);
        }
        if PROFILE { jit.sync_tree_profile(profile.as_deref_mut().unwrap()); }
        debug_assert!(memory.bytes.initialized_len() >= memory_end);
        let len = memory.bytes.len();
        // SAFETY: validated tree metadata bounds all native descendants and
        // their initialized register/memory slices. The root Call has already
        // initialized its frame/args/registers. Guards above cover full guest
        // working-memory/depth limits and budget. Heap cannot grow in a tree.
        // Guest arenas, registers, counters and cursor have distinct storage;
        // all remain exclusively owned and stable through this synchronous
        // same-thread call, with no code publication or protection change.
        let run = unsafe { jit.run_tree(function, budget, return_address,
            self.profile_table.as_ptr(), registers[register_base..].as_mut_ptr(), base,
            memory.bytes.prepared_mut_ptr(), len, memory.readonly_end,
            memory.heap.bytes.as_mut_ptr(), memory.heap.bytes.len()) }?
            .ok_or("prepared native tree unexpectedly declined at entry")?;
        memory.bytes.commit_native_len(run.memory_len)?;
        memory.peak = memory.peak.max(run.peak_linear + fixed.unwrap());
        self.entries += 1;
        self.calls += run.calls;
        self.instructions += run.instructions;
        Ok(Some(run.instructions))
    }
}
