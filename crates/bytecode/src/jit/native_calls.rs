//! Experimental complete acyclic native call trees. No VM transition is wired
//! yet: direct-entry differential tests exercise this ABI before integration.
use super::*;
use super::trees::{Plan, analyze};

#[repr(C)]
struct TreeCursor {
    base: Cursor,
    memory_len: usize,
    peak_linear: usize,
    return_address: usize,
    profile_table: *const *mut u64,
    calls: u64,
}
#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
const _: () = {
    assert!(std::mem::offset_of!(TreeCursor, base) == 0);
    assert!(std::mem::offset_of!(TreeCursor, memory_len) == 16);
    assert!(std::mem::offset_of!(TreeCursor, peak_linear) == 24);
    assert!(std::mem::offset_of!(TreeCursor, return_address) == 32);
    assert!(std::mem::offset_of!(TreeCursor, profile_table) == 40);
    assert!(std::mem::offset_of!(TreeCursor, calls) == 48);
    assert!(std::mem::size_of::<TreeCursor>() == 56);
};

pub(super) struct State {
    plans: Vec<Result<Plan, trees::Decline>>,
    prepared: Vec<bool>,
    pub entries: Vec<Option<Entry>>,
    pub bytes: usize,
    pub operations: usize,
    pub compiled: usize,
    pub declined: usize,
}
pub(super) struct Entry {
    wrapper: usize,
    internal: usize,
    pub ends: Vec<Option<usize>>,
}
struct Staged<'a> {
    words: Vec<u32>,
    internal: usize,
    ends: Vec<Option<usize>>,
    assertions: Vec<Assertion<'a>>,
}
#[derive(Debug)]
pub(crate) struct TreeRun {
    pub instructions: u64,
    pub memory_len: usize,
    pub peak_linear: usize,
    pub calls: u64,
}

impl<'a> Jit<'a> {
    /// Analyze once on first experimental use. Prepare all cold dependencies
    /// before publishing any parent. Immutable entries share the region arena.
    pub(crate) fn ensure_tree(&mut self, id: usize) -> Result<Option<Plan>, String> {
        if self.trees.is_none() {
            let n = self.program.functions.len();
            self.trees = Some(State { plans: analyze(self.program), prepared: vec![false; n],
                entries: (0..n).map(|_| None).collect(), bytes: 0, operations: 0,
                compiled: 0, declined: 0 });
        }
        let tree = self.trees.as_ref().unwrap();
        let Ok(plan) = tree.plans[id] else { return Ok(None); };
        if !tree.prepared[id] {
            let started = std::time::Instant::now();
            let prepared = self.prepare_tree_dependencies(id);
            self.compile_nanos += started.elapsed().as_nanos();
            prepared?;
        }
        Ok(self.trees.as_ref().unwrap().entries[id].as_ref().map(|_| plan))
    }

    fn prepare_tree_dependencies(&mut self, root: usize) -> Result<(), String> {
        let mut pending = vec![(root, false)];
        while let Some((id, children_ready)) = pending.pop() {
            if self.trees.as_ref().unwrap().prepared[id] { continue; }
            if !children_ready {
                pending.push((id, true));
                for op in &self.program.functions[id].code {
                    if let Op::Call { function, .. } = op { pending.push((*function, false)); }
                }
                continue;
            }
            let available = self.program.functions[id].code.iter().all(|op| match op {
                Op::Call { function, .. } => self.trees.as_ref().unwrap().entries[*function].is_some(),
                _ => true,
            });
            let staged = if available { self.emit_tree(id, (self.capacity - self.bytes) / 4) } else { Ok(None) };
            let staged = match staged {
                Ok(Some(s)) => s,
                Ok(None) | Err(EmitError::Limit(_)) => {
                    let tree = self.trees.as_mut().unwrap();
                    tree.prepared[id] = true;
                    tree.declined += 1;
                    continue;
                }
                Err(EmitError::InvalidRelocation(message)) => return Err(message.into()),
            };
            self.assertions.try_reserve(staged.assertions.len()).map_err(|_| "JIT fault table allocation failed")?;
            if self.code.is_none() { self.code = Some(platform::Code::reserve(self.capacity)?); }
            let offset = self.code.as_mut().unwrap().append(&staged.words)?;
            let bytes = staged.words.len() * 4;
            self.bytes += bytes;
            self.assertions.extend(staged.assertions);
            let tree = self.trees.as_mut().unwrap();
            tree.entries[id] = Some(Entry { wrapper: offset, internal: offset + staged.internal * 4, ends: staged.ends });
            tree.prepared[id] = true;
            tree.compiled += 1;
            tree.bytes += bytes;
            tree.operations += self.program.functions[id].code.len();
        }
        Ok(())
    }

    fn emit_tree(&self, id: usize, word_budget: usize) -> Result<Option<Staged<'a>>, EmitError> {
        let f = &self.program.functions[id];
        let reads = read_registers(f);
        let fills = local_fills(f);
        let mut wrapper = Assembler::default();
        wrapper.emit(0xa9bf7bf3); // stp x19,lr,[sp,#-16]!
        wrapper.mov(19, 7);
        if self.uses_heap { wrapper.mov(7, 5); wrapper.mov(8, 6); }
        wrapper.emit(0xf940126f); // ldr x15,[x19,#32]: root return destination
        let wrapper_call = wrapper.words.len();
        wrapper.emit(0x94000000); // bl internal entry
        wrapper.return_to_vm();
        let internal = wrapper.words.len();
        wrapper.words[wrapper_call] |= branch_displacement(wrapper_call, internal, 26, CodegenLimit::Jump)?;
        wrapper.emit(0xa9bc57f4); // stp x20,x21,[sp,#-64]!
        wrapper.emit(0xa9017bf6); // stp x22,lr,[sp,#16]
        wrapper.emit(0xa90207e0); // stp x0,x1,[sp,#32]
        if self.profiled {
            wrapper.emit(0xf9400669); // ldr x9,[x19,#8]
            wrapper.emit(0xf9001be9); // str x9,[sp,#48]
        }
        wrapper.mov(20, 15);
        let mut words = wrapper.words;
        let mut ends = vec![None; f.code.len()];
        let mut entries = vec![None; f.code.len()];
        let mut starts = vec![false; f.code.len()];
        let mut assertions = vec![];
        let mut links = vec![];
        starts[0] = true;
        for (pc, op) in f.code.iter().enumerate() {
            match op {
                Op::Jump { target } => starts[*target] = true,
                Op::Switch { cases, otherwise, .. } => {
                    starts[*otherwise] = true;
                    for (_, target) in cases { starts[*target] = true; }
                }
                _ => {}
            }
            if terminal(op) && pc + 1 < starts.len() { starts[pc + 1] = true; }
        }
        let mut pc = 0;
        while pc < f.code.len() {
            let start = pc;
            pc += 1;
            while pc < f.code.len() && pc - start < 1024 && !starts[pc] { pc += 1; }
            entries[start] = Some(words.len());
            ends[start] = Some(pc);
            let mut a = Assembler { heap: self.uses_heap, reads: &reads, frame_size: f.frame_size,
                region_start: start, region_end: pc, ..Assembler::default() };
            // The checked whole-tree bound guarantees enough budget for every
            // path, including nested bodies. There is no partial-budget exit.
            a.emit(0xf9400269);
            a.imm(10, (pc - start) as u64);
            a.three(0xcb000000, 9, 9, 10);
            a.emit(0xf9000269);
            if self.profiled {
                a.emit(0xf940066a);
                a.imm(11, start as u64 * 8);
                a.three(0x8b000000, 10, 10, 11);
                a.emit(0xf940014b);
                a.emit(0x9100056b);
                a.emit(0xf900014b);
            }
            let tail = terminal(&f.code[pc - 1]).then_some(&f.code[pc - 1]);
            for index in start..pc - usize::from(tail.is_some()) {
                a.current_pc = index;
                match &f.code[index] {
                    Op::Assert { value, expected, message } => {
                        let code = assertion_code(self.assertions.len(), assertions.len())?;
                        assertions.push(Assertion { message, function: &f.name, kind: FaultKind::Assertion });
                        a.assertion(*value, *expected, code);
                    }
                    op => if let Some(fill) = fills.get(&index) { a.local_fill(*fill); } else { a.lower(op); },
                }
            }
            a.flush_facts(start, pc);
            a.current_pc = pc - 1;
            match tail {
                Some(Op::Call { function, args, destination }) => {
                    let callee = &self.program.functions[*function];
                    let target = self.trees.as_ref().unwrap().entries[*function].as_ref()
                        .ok_or(EmitError::InvalidRelocation("unprepared native call dependency"))?.internal / 4;
                    a.tree_call(f, callee, *function, args, *destination, self.profiled,
                        self.bytes / 4 + words.len(), target)?;
                    a.successor(pc);
                }
                Some(Op::Return) => a.tree_return(f)?,
                Some(Op::Trap { message }) => {
                    let code = assertion_code(self.assertions.len(), assertions.len())?;
                    assertions.push(Assertion { message, function: &f.name, kind: FaultKind::Trap });
                    a.imm(0, code);
                    a.tree_epilogue();
                }
                _ => a.exit(tail, pc)?,
            }
            let failures = std::mem::take(&mut a.failures);
            for kind in [Failure::Memory, Failure::DivisionZero, Failure::DivisionOverflow] {
                if !failures.iter().any(|(_, k)| *k == kind) { continue; }
                let target = a.words.len();
                a.imm(0, kind as u64);
                a.tree_epilogue();
                for &(at, failure) in &failures { if failure == kind { a.patch_conditional(at, target)?; } }
            }
            for (at, code) in std::mem::take(&mut a.assertions) {
                let target = a.words.len();
                a.imm(0, code);
                a.tree_epilogue();
                a.patch_conditional(at, target)?;
            }
            links.extend(a.links.iter().map(|(at, successor)| (words.len() + at, *successor)));
            if a.words.len() > word_budget.saturating_sub(words.len()) { return Ok(None); }
            words.extend(a.words);
        }
        for (at, successor) in links {
            let target = entries.get(successor).copied().flatten()
                .ok_or(EmitError::InvalidRelocation("native tree has an incomplete successor"))?;
            patch_jump(&mut words, at, target)?;
        }
        Ok(Some(Staged { words, internal, ends, assertions }))
    }

    /// Execute a prepared complete tree, or decline before any guest progress.
    ///
    /// # Safety
    /// The validated function's root frame and arguments are already reserved
    /// and initialized; root registers obey the VM's initial-zero contract.
    /// `registers` covers plan.register_slots initialized u128s and `memory`
    /// covers base + plan.frame_span initialized bytes, exclusively borrowed
    /// and stable until return. Only [0,len) is initially guest-visible. Guest
    /// memory, heap, registers and host metadata are distinct allocations.
    /// Heap/readonly and thread/code protection follow Jit::run's contract.
    /// When profiled, the table has one nonnull pointer per function to a
    /// stable initialized counter array of that function's bytecode length.
    /// The caller has conservatively prechecked depth and live memory limits.
    pub(crate) unsafe fn run_tree(&self, id: usize, budget: u64, return_address: usize,
        profile_table: *const *mut u64, registers: *mut u128, base: usize,
        memory: *mut u8, len: usize, readonly: usize, heap: *mut u8, heap_len: usize,
    ) -> Result<Option<TreeRun>, String> {
        let Some(tree) = &self.trees else { return Ok(None); };
        let Some(entry) = &tree.entries[id] else { return Ok(None); };
        let plan = tree.plans[id].map_err(|_| "published native tree has no plan")?;
        if budget < plan.instructions { return Ok(None); }
        let profile_hits = if self.profiled { unsafe { *profile_table.add(id) } } else { std::ptr::null_mut() };
        let mut cursor = TreeCursor { base: Cursor { remaining: budget, profile_hits }, memory_len: len,
            peak_linear: len, return_address, profile_table, calls: 0 };
        let status = unsafe { self.code.as_ref().ok_or("missing tree code")?.call(entry.wrapper,
            registers, base, memory, len, readonly, heap, heap_len, &mut cursor.base) };
        if status >= FAILURE_MIN { return Err(self.fault_message(status)?); }
        if status != 0 || cursor.memory_len != base { return Err("JIT tree returned an invalid completion".into()); }
        let instructions = budget.checked_sub(cursor.base.remaining)
            .filter(|n| *n != 0 && *n <= plan.instructions).ok_or("JIT tree returned an invalid instruction count")?;
        if cursor.peak_linear > base.checked_add(plan.frame_span).ok_or("native tree span overflow")? {
            return Err("JIT tree exceeded its prepared memory extent".into());
        }
        Ok(Some(TreeRun { instructions, memory_len: cursor.memory_len, peak_linear: cursor.peak_linear, calls: cursor.calls }))
    }
}

fn terminal(op: &Op) -> bool {
    branch(op) || matches!(op, Op::Call { .. } | Op::Return | Op::Trap { .. })
}

impl Assembler<'_> {
    fn tree_epilogue(&mut self) {
        self.emit(0xf9000a63); // str x3,[x19,#16]: live extent, also on faults
        self.emit(0xa9417bf6); // ldp x22,lr,[sp,#16]
        self.emit(0xa8c457f4); // ldp x20,x21,[sp],#64
        self.emit(0xd65f03c0);
    }

    fn tree_call(&mut self, caller: &Function, callee: &Function, callee_id: usize,
        args: &[Reg], destination: Reg, profiled: bool, global_start: usize, target: usize,
    ) -> Result<(), EmitError> {
        self.evict_cached(true);
        self.imm(9, (callee.frame_align - 1) as u64);
        self.three(0x8b000000, 21, 3, 9);
        self.imm(9, !((callee.frame_align - 1) as u64));
        self.three(0x8a000000, 21, 21, 9); // aligned child base
        self.imm(9, caller.registers as u64 * 16);
        self.three(0x8b000000, 22, 0, 9);
        self.three(0x8b000000, 11, 2, 3); // old live end as host pointer
        self.imm(9, callee.frame_size.max(1) as u64);
        self.three(0x8b000000, 3, 21, 9); // publish new live end before args
        self.three(0x8b000000, 12, 2, 3);
        self.zero_range()?;
        self.emit(0xf9400e69); // ldr x9,[x19,#24]
        self.cmp(3, 9);
        self.emit(0x9a892069); // csel x9,x3,x9,hs: max(new live end, old peak)
        self.emit(0xf9000e69);
        self.emit(0xf9401a69); // ldr x9,[x19,#48]: nested calls
        self.emit(0x91000529);
        self.emit(0xf9001a69);
        for (source, slot) in args.iter().zip(&callee.args) {
            self.address(11, *source, slot.size, false);
            self.imm(12, slot.offset as u64);
            self.three(0x8b000000, 12, 21, 12);
            // Validated slots are inside the now-live child frame.
            self.three(0x8b000000, 12, 2, 12);
            self.abi_copy(slot.size)?;
        }
        if crate::registers::needs_initial_zeroes(callee) {
            self.mov(11, 22);
            self.imm(12, callee.registers as u64 * 16);
            self.three(0x8b000000, 12, 22, 12);
            self.zero_range()?;
        }
        self.get(15, destination, false);
        self.mov(0, 22);
        self.mov(1, 21);
        if profiled {
            self.emit(0xf9401669); // ldr x9,[x19,#40]: profile table
            self.imm(10, callee_id as u64 * 8);
            self.three(0x8b000000, 9, 9, 10);
            self.emit(0xf9400129);
            self.emit(0xf9000669);
        }
        let at = global_start.checked_add(self.words.len())
            .ok_or(EmitError::Limit(CodegenLimit::Jump))?;
        // Dependencies precede this unpublished function in the same arena.
        if target >= global_start { return Err(EmitError::InvalidRelocation("native call target is not published")); }
        self.emit(0x94000000 | branch_displacement(at, target, 26, CodegenLimit::Jump)?);
        self.cmp(0, 31);
        let success = self.words.len();
        self.emit(0x54000000); // b.eq restore caller
        self.tree_epilogue(); // fault: no copy or further guest operation
        self.patch_conditional(success, self.words.len())?;
        self.emit(0xa94207e0); // ldp x0,x1,[sp,#32]
        if profiled {
            self.emit(0xf9401be9);
            self.emit(0xf9000669);
        }
        Ok(())
    }

    fn tree_return(&mut self, f: &Function) -> Result<(), EmitError> {
        self.evict_cached(true);
        self.imm(11, f.result.offset as u64);
        self.three(0x8b000000, 11, 1, 11);
        self.three(0x8b000000, 11, 2, 11);
        self.mov(12, 20);
        self.checked_address(12, f.result.size, true);
        self.abi_copy(f.result.size)?;
        self.mov(3, 1); // Return retains alignment padding before this frame.
        self.mov(0, 31);
        self.tree_epilogue();
        Ok(())
    }

    /// Zero the prechecked host range [x11,x12); no other persistent state.
    fn zero_range(&mut self) -> Result<(), EmitError> {
        let chunks = self.words.len();
        self.three(0xcb000000, 9, 12, 11);
        self.imm(10, 16);
        self.cmp(9, 10);
        let tail = self.words.len();
        self.emit(0x54000003);
        self.emit(0xa8817d7f); // stp xzr,xzr,[x11],#16
        let repeat = self.words.len();
        self.emit(0x14000000);
        patch_jump(&mut self.words, repeat, chunks)?;
        self.patch_conditional(tail, self.words.len())?;
        let bytes = self.words.len();
        self.cmp(11, 12);
        let done = self.words.len();
        self.emit(0x54000000);
        self.emit(0x3800157f); // strb wzr,[x11],#1
        let repeat = self.words.len();
        self.emit(0x14000000);
        patch_jump(&mut self.words, repeat, bytes)?;
        self.patch_conditional(done, self.words.len())?;
        Ok(())
    }

    /// Memmove between complete prechecked host ranges, x11 -> x12. Argument
    /// slots can overlap each other or their sources; snapshot only this copy.
    fn abi_copy(&mut self, size: usize) -> Result<(), EmitError> {
        if size == 0 { return Ok(()); }
        if size <= 16 {
            self.load_mem(9, 10, 11, size);
            self.store_mem(9, 10, 12, size);
        } else if size <= 128 {
            let chunks = size / 16;
            let tail = size % 16;
            for q in 0..chunks as u32 { self.emit(0x3dc00000 | (q << 10) | (11 << 5) | q); }
            if tail != 0 {
                self.emit(0x91000000 | ((chunks as u32 * 16) << 10) | (11 << 5) | 11);
                self.load_mem(9, 10, 11, tail);
            }
            for q in 0..chunks as u32 { self.emit(0x3d800000 | (q << 10) | (12 << 5) | q); }
            if tail != 0 {
                self.emit(0x91000000 | ((chunks as u32 * 16) << 10) | (12 << 5) | 12);
                self.store_mem(9, 10, 12, tail);
            }
        } else {
            self.imm(9, size as u64);
            self.cmp(12, 11);
            let forward = self.words.len();
            self.emit(0x54000009); // b.ls forward
            self.three(0x8b000000, 11, 11, 9);
            self.three(0x8b000000, 12, 12, 9);
            let backward = self.words.len();
            self.emit(0x385ffd6a); // ldrb w10,[x11,#-1]!
            self.emit(0x381ffd8a); // strb w10,[x12,#-1]!
            self.emit(0xf1000529); // subs x9,x9,#1
            let again = self.words.len();
            self.emit(0x54000001);
            self.patch_conditional(again, backward)?;
            let done = self.words.len();
            self.emit(0x14000000);
            self.patch_conditional(forward, self.words.len())?;
            let next = self.words.len();
            self.emit(0x3840156a); // ldrb w10,[x11],#1
            self.emit(0x3800158a); // strb w10,[x12],#1
            self.emit(0xf1000529);
            let again = self.words.len();
            self.emit(0x54000001);
            self.patch_conditional(again, next)?;
            // patch_jump needs the label to be an actual instruction.
            self.emit(0xd503201f); // nop: common continuation
            let target = self.words.len() - 1;
            patch_jump(&mut self.words, done, target)?;
        }
        Ok(())
    }
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
#[path = "native_calls_tests.rs"]
mod tests;
