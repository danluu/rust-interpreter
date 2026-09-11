//! Optional direct Call stubs linked with ordinary generated regions.
use super::*;
use super::native_calls::TreeCursor;

#[derive(Clone, Copy, Default, Debug)]
pub(crate) struct RegionPlan {
    child_span: usize,
    child_align: usize,
    child_registers: usize,
    pub depth: usize,
}
impl RegionPlan {
    fn add(&mut self, plan: trees::Plan) {
        self.child_span = self.child_span.max(plan.frame_span);
        self.child_align = self.child_align.max(plan.frame_align);
        self.child_registers = self.child_registers.max(plan.register_slots);
        self.depth = self.depth.max(plan.depth);
    }
    /// Bounds start at CURRENT live memory/register ends, including padding
    /// retained by earlier VM calls. Sibling calls round at most to max align.
    pub fn requirements(self, memory: usize, registers: usize) -> Option<(usize, usize, usize)> {
        let align = self.child_align.max(1);
        let live_ceiling = memory.checked_add(align - 1)? & !(align - 1);
        Some((live_ceiling.checked_add(self.child_span)?,
            registers.checked_add(self.child_registers)?, live_ceiling))
    }
}

pub(crate) struct RegionRun {
    pub next: usize,
    pub instructions: u64,
    pub memory_len: usize,
    pub peak_linear: usize,
    pub tree_instructions: u64,
    pub calls: u64,
    pub stub_calls: u64,
}

impl<'a> Jit<'a> {
    pub(super) fn prepare_region_calls(&mut self, id: usize) -> Result<(), String> {
        let callees: BTreeSet<_> = self.program.functions[id].code.iter().filter_map(|op| match op {
            Op::Call { function, .. } => Some(*function), _ => None,
        }).collect();
        let mut plan = RegionPlan::default();
        for callee in callees {
            if let Some(child) = self.ensure_tree(callee)? { plan.add(child); }
        }
        self.region_plans[id] = plan;
        Ok(())
    }

    pub(super) fn emit_call_stub<'b>(&self, caller: &Function, pc: usize, callee_id: usize,
        args: &[Reg], destination: Reg, plan: trees::Plan, target: usize, global_start: usize,
        reads: &'b [Option<(usize, usize)>], values: Option<&'b values::Allocation>,
    ) -> Result<(Assembler<'b>, usize, usize), EmitError> {
        let mut a = Assembler { heap: self.uses_heap, reads, values, frame_size: caller.frame_size,
            region_start: pc, region_end: pc + 1, current_pc: pc, tree_caller_is_region: true,
            ..Assembler::default() };
        a.external_entry();
        let internal = a.words.len();
        a.emit(0xf9402269); // ldr x9,[x19,#64]: whole-caller storage readiness
        a.cmp(9, 31);
        let unready = a.words.len();
        a.emit(0x54000000); // b.eq decline, before any guest progress
        a.emit(0xf9400269);
        a.imm(10, plan.instructions + 1);
        a.cmp(9, 10);
        let short_budget = a.words.len();
        a.emit(0x54000003); // b.lo decline
        a.emit(0xd1000529); // sub x9,x9,#1: caller's Call only
        a.emit(0xf9000269);
        a.tree_push_frame(); // stub does not clobber its caller's assigned pairs
        a.emit(0xf9001fe9); // str x9,[sp,#56]: budget before descendants
        if self.profiled {
            a.emit(0xf940066a); // caller's ordinary block counters
            a.emit(0xf9001bea); // saved across child profile switching
            a.imm(11, pc as u64 * 8);
            a.three(0x8b000000, 10, 10, 11);
            a.emit(0xf940014b);
            a.emit(0x9100056b);
            a.emit(0xf900014b);
        }
        a.tree_call(caller, &self.program.functions[callee_id], callee_id, args, destination,
            self.profiled, global_start, target / 4)?;
        // tree_call has restored caller x0/x1 and profile pointer. Count only
        // descendant instructions here; the outer Call is in ordinary blocks.
        a.emit(0xf9401fe9); // before-child remaining budget
        a.emit(0xf940026a); // after-child remaining budget
        a.three(0xcb000000, 9, 9, 10);
        a.emit(0xf9401e6a); // ldr x10,[x19,#56]
        a.three(0x8b000000, 9, 9, 10);
        a.emit(0xf9001e69);
        a.emit(0xf9402669); // ldr x9,[x19,#72]: successful outer stubs
        a.emit(0x91000529);
        a.emit(0xf9002669);
        a.tree_restore_host_frame();
        a.successor(pc + 1); // ordinary entry frame and assigned pairs stay live
        let failures = std::mem::take(&mut a.failures);
        for kind in [Failure::Memory, Failure::DivisionZero, Failure::DivisionOverflow] {
            if !failures.iter().any(|(_, k)| *k == kind) { continue; }
            let target = a.words.len();
            a.imm(0, kind as u64);
            a.tree_epilogue(); // pop the internal AND ordinary wrapper frames
            for &(at, k) in &failures { if k == kind { a.patch_conditional(at, target)?; } }
        }
        let decline = a.words.len();
        a.return_pc(pc);
        a.patch_conditional(unready, decline)?;
        a.patch_conditional(short_budget, decline)?;
        let fallback = a.words.len();
        a.return_pc(pc + 1);
        Ok((a, internal, fallback))
    }

    /// Execute ordinary regions that may link to native Call stubs.
    ///
    /// # Safety
    /// In addition to Jit::run's ordinary entry/storage contract, this JIT was
    /// constructed with stubs enabled. When ready, memory and registers cover
    /// this function's RegionPlan from their current active ends, all backing
    /// bytes/elements are initialized, and depth/live-memory limits prechecked.
    /// All storage, including per-function tree-profile arrays/table, is stable
    /// and exclusive. When unready, generated stubs decline before dereferencing
    /// descendant storage. No allocation/publication occurs during this call.
    pub(crate) unsafe fn run_regions(&self, block: Block, pc: usize, code_len: usize,
        budget: u64, ready: bool, prepared_end: usize, profile_hits: *mut u64,
        profile_table: *const *mut u64, registers: *mut u128, base: usize,
        memory: *mut u8, len: usize, readonly: usize, heap: *mut u8, heap_len: usize,
    ) -> Result<RegionRun, String> {
        debug_assert!(self.native_call_stubs);
        let mut cursor = TreeCursor { base: Cursor { remaining: budget, profile_hits },
            memory_len: len, peak_linear: len, return_address: 0, profile_table, calls: 0,
            tree_instructions: 0, regions_ready: u64::from(ready), stub_calls: 0 };
        let status = unsafe { self.code.as_ref().ok_or("missing native region code")?.call(block.offset,
            registers, base, memory, len, readonly, heap, heap_len,
            std::ptr::addr_of_mut!(cursor).cast::<Cursor>()) };
        if status >= FAILURE_MIN { return Err(self.fault_message(status)?); }
        let executed = budget.checked_sub(cursor.base.remaining).ok_or("native region budget increased")?;
        if status > code_len as u64 || (executed == 0 && status != pc as u64) {
            return Err("native region returned an invalid continuation".into());
        }
        if cursor.memory_len < len || cursor.memory_len > cursor.peak_linear || cursor.peak_linear > prepared_end {
            return Err("native region returned an invalid memory extent".into());
        }
        if cursor.tree_instructions > executed || (!ready && (cursor.calls != 0 || cursor.stub_calls != 0)) {
            return Err("native region returned invalid call accounting".into());
        }
        Ok(RegionRun { next: status as usize, instructions: executed, memory_len: cursor.memory_len,
            peak_linear: cursor.peak_linear, tree_instructions: cursor.tree_instructions,
            calls: cursor.calls, stub_calls: cursor.stub_calls })
    }
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
#[path = "native_regions_tests.rs"]
mod tests;
