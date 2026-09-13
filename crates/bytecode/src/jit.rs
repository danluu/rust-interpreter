//! A small, direct AArch64 emitter for bytecode regions and their branch exits.
//!
//! The machine owns region dispatch and guest allocations. An explicit
//! experiment also compiles complete bounded native call trees.
//! Generated leaf functions receive current storage pointers on every entry;
//! they never retain pointers across a VM call or allocation. Unsupported
//! operations remain in our own interpreter. No assembler or codegen library
//! participates in producing the instructions.
use crate::{Binary, Function, Op, Program, Reg, Unary};
use std::collections::{BTreeMap, BTreeSet};

// The bounded-call experiment is staged independently of ordinary regions.
// Its metadata becomes live when the opt-in native transition is connected.
#[allow(dead_code)]
mod trees;
#[allow(dead_code)]
mod native_calls;
mod native_regions;
mod resumable;
mod call_slots;
mod code_dump;
mod values;
mod transfers;

#[cfg(test)]
mod limit_tests;
#[cfg(test)]
mod register_pair_tests;

// This cursor is host-owned and lives across exactly one generated-code call.
// Its pointers never enter guest registers or addressable guest memory.
#[repr(C)]
struct Cursor {
    remaining: u64,
    profile_hits: *mut u64,
}
#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
const _: () = {
    assert!(std::mem::offset_of!(Cursor, remaining) == 0);
    assert!(std::mem::offset_of!(Cursor, profile_hits) == 8);
    assert!(std::mem::size_of::<Cursor>() == 16);
};

#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
mod platform {
    use std::ffi::c_void;

    #[cfg(test)]
    std::arch::global_asm!(r#"
        .text
        .p2align 2
        .globl _rust_interp_jit_abi_probe
    _rust_interp_jit_abi_probe:
        stp x19, x20, [sp, #-32]!
        stp x29, x30, [sp, #16]
        mov x29, sp
        mov x20, x2
        mov x16, x0
        mov x17, x1
        mov x19, #0x1357
        ldp x0, x1, [x17]
        ldp x2, x3, [x17, #16]
        ldp x4, x5, [x17, #32]
        ldp x6, x7, [x17, #48]
        blr x16
        str x0, [x20]
        str x19, [x20, #8]
        mov x9, sp
        str x9, [x20, #16]
        str x29, [x20, #24]
        ldp x29, x30, [sp, #16]
        ldp x19, x20, [sp], #32
        ret
        .p2align 2
        .globl _rust_interp_tree_abi_probe
    _rust_interp_tree_abi_probe:
        stp x19, x20, [sp, #-112]!
        stp x21, x22, [sp, #16]
        stp x23, x24, [sp, #32]
        stp x25, x26, [sp, #48]
        stp x27, x28, [sp, #64]
        stp x29, x30, [sp, #80]
        str x2, [sp, #96]
        mov x29, sp
        mov x16, x0
        mov x17, x1
        mov x19, #0x1357
        mov x20, #0x2468
        mov x21, #0x3579
        mov x22, #0x468a
        mov x23, #0x579b
        mov x24, #0x68ac
        mov x25, #0x79bd
        mov x26, #0x8ace
        mov x27, #0x9bdf
        mov x28, #0xace0
        ldp x0, x1, [x17]
        ldp x2, x3, [x17, #16]
        ldp x4, x5, [x17, #32]
        ldp x6, x7, [x17, #48]
        blr x16
        ldr x10, [sp, #96]
        stp x0, x19, [x10]
        stp x20, x21, [x10, #16]
        stp x22, x29, [x10, #32]
        mov x9, sp
        str x9, [x10, #48]
        stp x23, x24, [x10, #56]
        stp x25, x26, [x10, #72]
        stp x27, x28, [x10, #88]
        ldp x19, x20, [sp]
        ldp x21, x22, [sp, #16]
        ldp x23, x24, [sp, #32]
        ldp x25, x26, [sp, #48]
        ldp x27, x28, [sp, #64]
        ldp x29, x30, [sp, #80]
        add sp, sp, #112
        ret
    "#);

    #[cfg(test)]
    unsafe extern "C" {
        fn rust_interp_jit_abi_probe(entry: *mut c_void, arguments: *const usize, output: *mut usize);
        fn rust_interp_tree_abi_probe(entry: *mut c_void, arguments: *const usize, output: *mut usize);
    }

    unsafe extern "C" {
        fn mmap(
            addr: *mut c_void,
            len: usize,
            prot: i32,
            flags: i32,
            fd: i32,
            off: i64,
        ) -> *mut c_void;
        fn munmap(addr: *mut c_void, len: usize) -> i32;
        fn pthread_jit_write_protect_np(enabled: i32);
        fn sys_icache_invalidate(start: *mut c_void, len: usize);
    }

    pub struct Code {
        ptr: *mut c_void,
        len: usize,
        used: usize,
    }
    impl Code {
        pub fn published(&self) -> (usize, &[u8]) {
            // SAFETY: append initializes exactly [ptr, ptr+used), used <= len.
            // The mapping is readable in execution mode, remains owned by
            // self, and cannot be unmapped or appended through this borrow.
            (self.ptr as usize, unsafe { std::slice::from_raw_parts(self.ptr.cast(), self.used) })
        }
        #[cfg(test)]
        pub unsafe fn tree_abi_probe(&self, offset: usize, arguments: [usize;8]) -> [usize;13] {
            assert!(offset < self.used);
            let mut output = [0;13];
            // Same exclusive storage contract as call(); the wrapper verifies
            // x19–x28 plus SP/LR, including persistent register pairs.
            unsafe {
                rust_interp_tree_abi_probe(self.ptr.cast::<u8>().add(offset).cast(), arguments.as_ptr(), output.as_mut_ptr());
            }
            output
        }
        #[cfg(test)]
        pub unsafe fn abi_probe(&self, offset: usize, arguments: [usize;8]) -> [usize;4] {
            assert!(offset < self.used);
            let mut output = [0;4];
            // Test callers supply the same live storage and cursor as call().
            // The assembly wrapper checks the native callee's x19 and SP.
            unsafe {
                rust_interp_jit_abi_probe(self.ptr.cast::<u8>().add(offset).cast(), arguments.as_ptr(), output.as_mut_ptr());
            }
            output
        }
        pub fn reserve(len: usize) -> Result<Self, String> {
            if len == 0 || len > super::MAX_CODE_BYTES {
                return Err("JIT code size outside supported range".into());
            }
            // One bounded MAP_JIT arena. Appending never moves older entries.
            // This VM is single-threaded; no guest code is running during writes.
            let ptr = unsafe { mmap(std::ptr::null_mut(), len, 7, 0x1802, -1, 0) };
            if ptr as isize == -1 {
                return Err(format!("allocate JIT code: {}", std::io::Error::last_os_error()));
            }
            Ok(Self { ptr, len, used: 0 })
        }
        pub fn append(&mut self, words: &[u32]) -> Result<usize, String> {
            let bytes = words.len().checked_mul(4).ok_or("JIT code size overflow")?;
            let end = self.used.checked_add(bytes).filter(|end| *end <= self.len)
                .ok_or("JIT arena capacity exceeded")?;
            let offset = self.used;
            if bytes != 0 {
                // All fallible work is complete before write protection changes.
                // Only immutable new words are copied; committed code is untouched.
                unsafe {
                    let destination = self.ptr.cast::<u8>().add(offset);
                    pthread_jit_write_protect_np(0);
                    std::ptr::copy_nonoverlapping(words.as_ptr().cast::<u8>(), destination, bytes);
                    pthread_jit_write_protect_np(1);
                    sys_icache_invalidate(destination.cast(), bytes);
                }
            }
            self.used = end;
            Ok(offset)
        }
        pub unsafe fn call(
            &self,
            offset: usize,
            registers: *mut u128,
            base: usize,
            memory: *mut u8,
            len: usize,
            readonly: usize,
            heap: *mut u8,
            heap_len: usize,
            cursor: *mut super::Cursor,
        ) -> u64 {
            type Entry = unsafe extern "C" fn(
                *mut u128,
                usize,
                *mut u8,
                usize,
                usize,
                *mut u8,
                usize,
                *mut super::Cursor,
            ) -> u64;
            // Only offsets generated by this emitter reach here. The mapping
            // lives through the call and all storage pointers cover the
            // validated machine's current allocations.
            let function: Entry = unsafe { std::mem::transmute(self.ptr.cast::<u8>().add(offset)) };
            unsafe { function(registers, base, memory, len, readonly, heap, heap_len, cursor) }
        }
    }
    impl Drop for Code {
        fn drop(&mut self) {
            unsafe {
                munmap(self.ptr, self.len);
            }
        }
    }
}

#[cfg(not(all(target_arch = "aarch64", target_os = "macos")))]
mod platform {
    pub struct Code;
    impl Code {
        pub fn published(&self) -> (usize, &[u8]) { unreachable!() }
        pub fn reserve(_: usize) -> Result<Self, String> {
            Err("the custom JIT currently requires Apple Silicon macOS".into())
        }
        pub fn append(&mut self, _: &[u32]) -> Result<usize, String> { unreachable!() }
        pub unsafe fn call(
            &self,
            _: usize,
            _: *mut u128,
            _: usize,
            _: *mut u8,
            _: usize,
            _: usize,
            _: *mut u8,
            _: usize,
            _: *mut super::Cursor,
        ) -> u64 {
            unreachable!()
        }
    }
}

#[derive(Clone, Copy)]
pub(crate) struct Block {
    pub offset: usize,
    pub end: usize,
}

struct Assertion<'a> {
    message: &'a str,
    function: &'a str,
    kind: FaultKind,
}

enum FaultKind { Assertion, Trap }

pub(crate) const MAX_CODE_BYTES: usize = 16 * 1024 * 1024;

struct CompiledFunction<'a> {
    #[cfg(test)]
    local_forwarding: Vec<(usize, &'static str)>,
    words: Vec<u32>,
    entries: Vec<Option<Block>>,
    resumes: Vec<Option<usize>>,
    operations: usize,
    assertions: Vec<Assertion<'a>>,
    register_pairs: usize,
    liveness_declined: bool,
}

pub(crate) struct Jit<'a> {
    // MAP_JIT write protection is per-thread. Make confinement intentional,
    // including on platforms whose placeholder Code type contains no pointer.
    _thread_bound: std::marker::PhantomData<std::rc::Rc<()>>,
    program: &'a Program,
    profiled: bool,
    uses_heap: bool,
    prepared: Vec<bool>,
    capacity: usize,
    code: Option<platform::Code>,
    pub blocks: Vec<Vec<Option<Block>>>,
    pub bytes: usize,
    pub operations: usize,
    pub compiled_functions: usize,
    pub declined_functions: usize,
    pub compile_nanos: u128,
    assertions: Vec<Assertion<'a>>,
    trees: Option<native_calls::State>,
    native_call_stubs: bool,
    pub region_plans: Vec<native_regions::RegionPlan>,
    pub call_stubs: usize,
    persistent_registers: bool,
    resumable: Option<resumable::Entries>,
    #[cfg(test)]
    disable_call_slot_hints: bool,
    pub register_functions: usize,
    pub register_pairs: usize,
    pub liveness_declines: usize,
}
impl<'a> Jit<'a> {
    pub fn new(program: &'a Program, profiled: bool, capacity: usize) -> Result<Self, String> {
        Self::new_with_call_stubs(program, profiled, capacity, false)
    }

    pub(crate) fn new_with_call_stubs(program: &'a Program, profiled: bool, capacity: usize,
        native_call_stubs: bool) -> Result<Self, String> {
        Self::new_with_options(program, profiled, capacity, native_call_stubs, false)
    }

    pub(crate) fn new_with_options(program: &'a Program, profiled: bool, capacity: usize,
        native_call_stubs: bool, persistent_registers: bool) -> Result<Self, String> {
        if capacity > MAX_CODE_BYTES { return Err("JIT code budget exceeds supported range".into()); }
        let uses_heap = !program.statics.is_empty() || program.functions.iter().flat_map(|f| &f.code).any(|op| {
            matches!(op, Op::Allocate { .. } | Op::Deallocate { .. } | Op::Reallocate { .. }
                | Op::CAllocate { .. } | Op::CReallocate { .. } | Op::CAlignedAllocate { .. })
        });
        Ok(Self { _thread_bound: std::marker::PhantomData, program, profiled, uses_heap, capacity, code: None,
            prepared: vec![false; program.functions.len()],
            blocks: vec![vec![]; program.functions.len()], bytes: 0, operations: 0,
            compiled_functions: 0, declined_functions: 0, compile_nanos: 0,
            assertions: vec![], trees: None, native_call_stubs, call_stubs: 0, resumable: None,
            #[cfg(test)]
            disable_call_slot_hints: false,
            persistent_registers, register_functions: 0, register_pairs: 0, liveness_declines: 0,
            region_plans: if native_call_stubs { vec![native_regions::RegionPlan::default(); program.functions.len()] } else { vec![] } })
    }

    /// Called at guest function entry, including TLS callbacks, never in the
    /// instruction dispatch loop. Failed/declined staging publishes no entries.
    #[inline(always)]
    pub fn ensure_function(&mut self, id: usize) -> Result<bool, String> {
        if self.prepared[id] { return Ok(false); }
        self.compile_function(id)
    }

    // Keep staging, timing and its stack frame off already prepared calls.
    #[cold]
    #[inline(never)]
    fn compile_function(&mut self, id: usize) -> Result<bool, String> {
        let start = std::time::Instant::now();
        let previous_nanos = self.compile_nanos;
        let result = self.prepare_function(id);
        // Tree preparation may occur inside this timed region. Its separate
        // counter is retained, but do not add the nested duration twice.
        self.compile_nanos = previous_nanos + start.elapsed().as_nanos();
        result
    }
    fn prepare_function(&mut self, id: usize) -> Result<bool, String> {
        if self.native_call_stubs { self.prepare_region_calls(id)?; }
        let remaining = (self.capacity - self.bytes) / 4;
        let staged = self.emit_function(&self.program.functions[id], remaining);
        self.finish_preparation(id, staged)
    }

    fn finish_preparation(&mut self, id: usize, staged: Result<Option<CompiledFunction<'a>>, EmitError>) -> Result<bool, String> {
        let mut staged = match staged {
            Ok(Some(staged)) => staged,
            Ok(None) | Err(EmitError::Limit(_)) => {
                // No words, entries or assertion identities have been published.
                // This function remains executable by our interpreter.
                self.prepared[id] = true;
                self.declined_functions += 1;
                return Ok(true);
            }
            Err(EmitError::InvalidRelocation(message)) => return Err(message.into()),
        };
        // Allocate the immutable target table before publishing code. A cold
        // or declined function keeps a null table and is entered by the VM.
        let mut resumes = Vec::new();
        if resumes.try_reserve_exact(staged.resumes.len()).is_err() {
            self.prepared[id] = true;
            self.declined_functions += 1;
            return Ok(true);
        }
        resumes.resize(staged.resumes.len(), 0usize);
        if !staged.words.is_empty() {
            self.assertions.try_reserve(staged.assertions.len())
                .map_err(|_| "JIT assertion table allocation failed")?;
            if self.code.is_none() { self.code = Some(platform::Code::reserve(self.capacity)?); }
            let offset = self.code.as_mut().unwrap().append(&staged.words)?;
            if let Some(tables) = &mut self.resumable {
                let arena = self.code.as_ref().unwrap().published().0;
                for (out, entry) in resumes.iter_mut().zip(&staged.resumes) {
                    if let Some(entry) = entry { *out = arena + offset + entry * 4; }
                }
                tables.publish(id, resumes);
            }
            for entry in staged.entries.iter_mut().flatten() { entry.offset += offset; }
            self.bytes += staged.words.len() * 4;
            self.compiled_functions += 1;
            self.register_functions += usize::from(staged.register_pairs != 0);
            self.register_pairs += staged.register_pairs;
        }
        self.operations += staged.operations;
        self.liveness_declines += usize::from(staged.liveness_declined);
        if self.native_call_stubs {
            self.call_stubs += staged.entries.iter().enumerate().filter(|(pc, entry)|
                entry.is_some() && matches!(self.program.functions[id].code[*pc], Op::Call { .. })).count();
        }
        self.assertions.extend(staged.assertions);
        self.blocks[id] = staged.entries;
        self.prepared[id] = true;
        Ok(true)
    }

    fn emit_function(&self, f: &'a Function, word_budget: usize) -> Result<Option<CompiledFunction<'a>>, EmitError> {
        let resumable = self.resumable.is_some();
        if self.resumable.as_ref().is_some_and(|tables| !tables.fits(f.code.len())) { return Ok(None); }
        let mut words = vec![];
        #[cfg(test)]
        let mut local_forwarding = vec![];
        let mut assertions = vec![];
        let mut operations = 0;
        let reads = read_registers(f);
        let values = self.persistent_registers.then(|| values::analyze(f)).flatten();
        let fills = local_fills(f);
        let slots = if resumable { call_slots::collect(f, self.program) } else { std::collections::BTreeMap::new() };
        #[cfg(test)]
        let slots = if self.disable_call_slot_hints { std::collections::BTreeMap::new() } else { slots };
        let native = |pc: usize| supported(&f.code[pc]) || fills.contains_key(&pc)
            || (resumable && transfers::supported(&f.code[pc]));
        let mut entries = vec![None; f.code.len()];
        let mut internal_entries = vec![None; f.code.len()];
        // The extra null entry handles a caller's one-past-code continuation.
        let mut resumes = if resumable { vec![None; f.code.len() + 1] } else { vec![] };
        let mut links = vec![];
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
        let mut pc = 0;
        while pc < f.code.len() {
            let start = pc;
            while pc < f.code.len()
                // Bound straight-line regions. Large constant/table
                // initializers otherwise put the shared memory-failure
                // return beyond AArch64's conditional branch range.
                && pc - start < 1024
                && (pc == start || !starts[pc])
                && native(pc)
            {
                pc += 1;
            }
            if pc - start >= if resumable { 1 } else { 3 } {
                let offset = words.len() * 4;
                let mut a = Assembler {
                    heap: self.uses_heap,
                    reads: &reads,
                    frame_size: f.frame_size,
                    region_start: start,
                    region_end: pc,
                    values: values.as_ref(),
                    resumable,
                    ..Assembler::default()
                };
                // External entries preserve the C ABI. Native successors
                // enter after this prologue and keep the same live storage.
                let resume = a.external_entry();
                if resumable { resumes[start] = Some(words.len() + resume); }
                internal_entries[start] = Some(words.len() + a.words.len());
                // Every native cycle consumes virtual instructions. When
                // the next block does not fit, let the VM execute its tail
                // one instruction at a time, preserving fault ordering.
                let budget = if resumable { resumable::BUDGET_REGISTER } else { 9 };
                if !resumable { a.emit(0xf9400269); } // ordinary Cursor.remaining
                a.imm(10, (pc - start) as u64);
                a.cmp(budget, 10);
                let budget_exit = a.words.len();
                a.emit(0x54000003); // b.lo budget_exit
                a.three(0xcb000000, budget, budget, 10);
                if !resumable { a.emit(0xf9000269); }
                if self.profiled {
                    // The VM supplies this function's stable counter array.
                    // The emitted offset is a validated PC, never guest data.
                    a.emit(0xf940066a); // ldr x10, [x19, #8]
                    a.imm(11, start as u64 * 8);
                    a.three(0x8b000000, 10, 10, 11);
                    a.emit(0xf940014b); // ldr x11, [x10]
                    a.emit(0x9100056b); // add x11, x11, #1
                    a.emit(0xf900014b); // str x11, [x10]
                }
                let terminal = branch(&f.code[pc-1]).then_some(&f.code[pc-1]);
                let body_end = pc-usize::from(terminal.is_some());
                for (index, op) in f.code[start..body_end].iter().enumerate() {
                    a.current_pc = start + index;
                    if let Op::Assert { value, expected, message } = op {
                        let code = assertion_code(self.assertions.len(), assertions.len())?;
                        assertions.push(Assertion { message, function: &f.name, kind: FaultKind::Assertion });
                        a.assertion(*value, *expected, code);
                    } else if let Some(fill) = fills.get(&(start + index)) {
                        a.local_fill(*fill);
                    } else if resumable && transfers::supported(op) {
                        a.copy_transfer(op)?;
                    } else {
                        a.lower(op);
                    }
                }
                a.flush_facts(start, pc);
                a.exit(terminal, pc)?;
                let failures = std::mem::take(&mut a.failures);
                for kind in [Failure::Memory, Failure::DivisionZero, Failure::DivisionOverflow] {
                    // Retain the existing memory tail. Add arithmetic tails
                    // only to regions that can actually take those exits.
                    if kind != Failure::Memory && !failures.iter().any(|(_, k)| *k == kind) {
                        continue;
                    }
                    let target = a.words.len();
                    a.imm(0, kind as u64);
                    a.return_to_vm();
                    for &(at, failure) in &failures {
                        if failure == kind { a.patch_conditional(at, target)?; }
                    }
                }
                // Assertion identities belong to this immutable program.
                // Return a fixed fault code; no guest address becomes a
                // host string pointer or a continuation.
                for (at, code) in std::mem::take(&mut a.assertions) {
                    let target = a.words.len();
                    a.imm(0, code);
                    a.return_to_vm();
                    a.patch_conditional(at, target)?;
                }
                let target = a.words.len();
                a.return_pc(start);
                a.patch_conditional(budget_exit, target)?;
                // Give each edge a safe VM exit first. After all blocks in
                // this function are laid out, compiled successors replace
                // these edges with direct branches to internal entries.
                for (at, successor) in std::mem::take(&mut a.links) {
                    let fallback = a.words.len();
                    a.return_pc(successor);
                    links.push((words.len() + at, successor, words.len() + fallback));
                }
                if a.words.len() > word_budget.saturating_sub(words.len()) {
                    return Ok(None);
                }
                #[cfg(test)]
                local_forwarding.extend(a.local_forwarding);
                words.extend(a.words);
                entries[start] = Some(Block { offset, end: pc });
                operations += pc - start;
            }
            if pc == start {
                if resumable && matches!(f.code[pc], Op::Call { .. } | Op::Return) {
                    let offset = words.len() * 4;
                    let (a, resume, internal) = self.emit_resumable_transition(f, pc, &reads, values.as_ref(), slots.get(&pc).map(Vec::as_slice))?;
                    if a.words.len() > word_budget.saturating_sub(words.len()) { return Ok(None); }
                    resumes[pc] = Some(words.len() + resume);
                    internal_entries[pc] = Some(words.len() + internal);
                    entries[pc] = Some(Block { offset, end: pc + 1 });
                    operations += 1;
                    words.extend(a.words);
                }
                if self.native_call_stubs {
                    if let Op::Call { function, args, destination } = &f.code[pc] {
                        if let Some((plan, target)) = self.ready_tree(*function) {
                            let offset = words.len() * 4;
                            let (a, internal, fallback) = self.emit_call_stub(f, pc, *function, args, *destination,
                                plan, target, self.bytes / 4 + words.len(), &reads, values.as_ref())?;
                            if a.words.len() > word_budget.saturating_sub(words.len()) { return Ok(None); }
                            internal_entries[pc] = Some(words.len() + internal);
                            // The stub already supplies a safe VM successor;
                            // successful edges are linked exactly like regions.
                            links.extend(a.links.iter().map(|&(at, successor)|
                                (words.len() + at, successor, words.len() + fallback)));
                            entries[pc] = Some(Block { offset, end: pc + 1 });
                            operations += 1;
                            words.extend(a.words);
                        }
                    }
                }
                pc += 1;
            }
        }
        for (at, successor, fallback) in links {
            let target = internal_entries.get(successor).copied().flatten().unwrap_or(fallback);
            patch_jump(&mut words, at, target)?;
        }
        Ok(Some(CompiledFunction { words, entries, resumes, operations, assertions,
            register_pairs: values.as_ref().map_or(0, |v| v.registers.len()),
            liveness_declined: self.persistent_registers && values.is_none(),
            #[cfg(test)] local_forwarding }))
    }
    /// Execute a region and any linked successors in the same guest function.
    ///
    /// # Safety
    /// `block` must be an entry published by this JIT for the current function,
    /// and neither it nor its native successors may contain Call stubs (use
    /// run_regions with the extended cursor for those functions).
    /// and `code_len` must be that function's bytecode length. `registers` must
    /// address its complete, initialized u128 register slice. `memory` and `heap`
    /// must address distinct live byte arenas of `len` and `heap_len` bytes;
    /// `base` identifies the function's reserved frame and `readonly <= len`.
    /// When profiling, `profile_hits` must address `code_len` initialized u64s;
    /// otherwise it may be null. Host metadata must not alias guest storage.
    ///
    /// All storage is exclusively owned for this call and must remain at stable
    /// addresses. No allocation, Vec growth, code append, concurrent guest call,
    /// or write-protection change may occur until return. Call on the JIT's
    /// owning thread with executable protection enabled. Generated code uses
    /// the little-endian AArch64 macOS ABI; no other platform is implemented.
    // Keep this transition in the VM loop even when cold fault paths grow.
    #[inline(always)]
    pub unsafe fn run(
        &self,
        block: Block,
        code_len: usize,
        budget: u64,
        profile_hits: *mut u64,
        registers: *mut u128,
        base: usize,
        memory: *mut u8,
        len: usize,
        readonly: usize,
        heap: *mut u8,
        heap_len: usize,
    ) -> Result<(usize, u64), String> {
        let mut cursor = Cursor { remaining: budget, profile_hits };
        let result = unsafe {
            self.code.as_ref().ok_or("missing JIT code")?.call(
                block.offset,
                registers,
                base,
                memory,
                len,
                readonly,
                heap,
                heap_len,
                &mut cursor,
            )
        };
        if result >= FAILURE_MIN {
            Err(self.fault_message(result)?)
        } else {
            // Only emitted constants become PCs. Permit code_len itself so a
            // missing terminator retains the VM's budget-before-invalid-PC
            // ordering; internal edges never branch outside the function.
            if result > code_len as u64 { return Err("JIT returned an invalid continuation".into()); }
            let executed = budget.checked_sub(cursor.remaining)
                .filter(|count| *count != 0).ok_or("JIT made no instruction progress")?;
            Ok((result as usize, executed))
        }
    }

    fn fault_message(&self, result: u64) -> Result<String, String> {
        let message = if result == Failure::Memory as u64 {
                "JIT guest memory access failed"
            } else if result == Failure::DivisionZero as u64 {
                "integer division by zero"
            } else if result == Failure::DivisionOverflow as u64 {
                "signed division overflow"
            } else {
                let assertion = self.assertions.get((ASSERTION_FAILURE_BASE - result) as usize)
                    .ok_or("JIT returned an invalid assertion identity")?;
                let kind = match assertion.kind { FaultKind::Assertion => "assertion", FaultKind::Trap => "trap" };
                return Ok(format!("guest {kind}: {} in {}", assertion.message, assertion.function));
            };
        Ok(message.into())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum CodegenLimit {
    ConditionalBranch,
    Jump,
    Assertions,
}

#[derive(Debug, PartialEq, Eq)]
enum EmitError {
    Limit(CodegenLimit),
    InvalidRelocation(&'static str),
}

fn assertion_code(published: usize, staged: usize) -> Result<u64, EmitError> {
    published.checked_add(staged)
        .and_then(|index| u64::try_from(index).ok())
        .and_then(|index| ASSERTION_FAILURE_BASE.checked_sub(index))
        .filter(|code| *code >= FAILURE_MIN)
        .ok_or(EmitError::Limit(CodegenLimit::Assertions))
}

// AArch64 displacements count four-byte instructions and are signed. Widen
// before subtraction so very large staging offsets cannot wrap into range.
fn branch_displacement(at: usize, target: usize, bits: u8, limit: CodegenLimit) -> Result<u32, EmitError> {
    let delta = target as i128 - at as i128;
    let range = 1i128 << (bits - 1);
    if !(-range..range).contains(&delta) { return Err(EmitError::Limit(limit)); }
    Ok((delta as u32) & ((1u32 << bits) - 1))
}

fn patch_jump(words: &mut [u32], at: usize, target: usize) -> Result<(), EmitError> {
    if at >= words.len() || target >= words.len() || words[at] != 0x14000000 {
        return Err(EmitError::InvalidRelocation("invalid JIT link relocation"));
    }
    words[at] |= branch_displacement(at, target, 26, CodegenLimit::Jump)?;
    Ok(())
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod link_tests {
    use super::*;
    use crate::{Slot, VERSION};

    #[test]
    fn every_linked_exit_preserves_the_native_abi_and_cursor() {
        for (left, right, terminal, expected) in [
            (0,1,Op::Imm {dst:0,value:2},6),
            (0,1,Op::Load {dst:2,address:0,size:8},Failure::Memory as u64),
            (0,1,Op::Binary {dst:2,overflow:3,op:Binary::Div,a:1,b:0,bits:64,signed:false},Failure::DivisionZero as u64),
            (1u128<<63,u64::MAX as u128,Op::Binary {dst:2,overflow:3,op:Binary::Div,a:0,b:1,bits:64,signed:true},Failure::DivisionOverflow as u64),
            (0,1,Op::Assert {value:0,expected:true,message:"ABI fault".into()},ASSERTION_FAILURE_BASE),
        ] {
            let program=Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,
                data:vec![0;16],statics:vec![],thread_locals:vec![],
                functions:vec![Function {name:"abi".into(),frame_size:64,frame_align:16,registers:4,
                    args:vec![],result:Slot {offset:0,size:8},code:vec![
                        Op::Imm {dst:0,value:left},Op::Imm {dst:1,value:right},Op::Jump {target:3},
                        terminal,Op::Imm {dst:2,value:2},Op::Jump {target:6},Op::Return]}]};
            crate::validate(&program).unwrap();
            for profiled in [false,true] {
                let mut jit = Jit::new(&program, profiled, MAX_CODE_BYTES).unwrap();
                jit.ensure_function(0).unwrap();
                for budget in [4,100] {
                    let mut registers=vec![0u128;4];let mut memory=vec![0u8;80];let mut hits=vec![0u64;7];
                    let mut cursor=Cursor {remaining:budget,profile_hits:if profiled {hits.as_mut_ptr()} else {std::ptr::null_mut()}};
                    let arguments=[registers.as_mut_ptr() as usize,16,memory.as_mut_ptr() as usize,memory.len(),16,
                        0,0,(&mut cursor as *mut Cursor) as usize];
                    let output=unsafe {jit.code.as_ref().unwrap().abi_probe(jit.blocks[0][0].unwrap().offset,arguments)};
                    assert_eq!(output[0] as u64,if budget==4 {3} else {expected});
                    assert_eq!(output[1],0x1357);assert_eq!(output[2],output[3]);
                    assert_eq!(cursor.remaining,if budget==4 {1} else {94});
                    if profiled {assert_eq!(hits[0],1);assert_eq!(hits[3],u64::from(budget!=4));}
                    else {assert_eq!(hits,vec![0;7]);}
                }
            }
        }
    }

    #[test]
    fn link_relocations_accept_only_bounded_branch_placeholders() {
        let mut words=vec![0x14000000;5];
        patch_jump(&mut words,0,4).unwrap();assert_eq!(words[0],0x14000004);
        patch_jump(&mut words,4,0).unwrap();assert_eq!(words[4],0x17fffffc);
        assert!(patch_jump(&mut words,0,4).is_err());
        assert!(patch_jump(&mut words,5,0).is_err());
        assert!(patch_jump(&mut words,1,5).is_err());
    }
}

fn read_registers(f: &Function) -> Vec<Option<(usize, usize)>> {
    let mut used: Vec<Option<(usize, usize)>> = vec![None; f.registers];
    for (pc, op) in f.code.iter().enumerate() {
        let mut mark = |r: Reg| {
            let range = used[r as usize].get_or_insert((pc, pc));
            range.1 = pc;
        };
        crate::registers::visit_registers(op, &mut mark, |_| {});
    }
    used
}
fn branch(op: &Op) -> bool {
    matches!(op, Op::Jump {..} | Op::Switch {..})
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct LocalFill {
    offset: usize,
    size: usize,
    byte: u8,
}

// A narrow compiler-independent peephole: three literal definitions followed
// by FillBytes. No branch may enter after the Local definition, and helpers
// must be distinct. This proof survives a native region-size split because
// the original register reads still govern spills and exact-budget VM tails.
fn local_fills(function: &Function) -> BTreeMap<usize, LocalFill> {
    let mut entries = vec![false; function.code.len()];
    for op in &function.code {
        match op {
            Op::Jump { target } => entries[*target] = true,
            Op::Switch { cases, otherwise, .. } => {
                entries[*otherwise] = true;
                for (_, target) in cases { entries[*target] = true; }
            }
            _ => {}
        }
    }
    let mut fills = BTreeMap::new();
    for pc in 3..function.code.len() {
        let Op::FillBytes { address, value, size } = &function.code[pc] else { continue; };
        let Op::Local { dst: address_reg, offset } = &function.code[pc-3] else { continue; };
        let Op::Imm { dst: value_reg, value: byte } = &function.code[pc-2] else { continue; };
        let Op::Imm { dst: size_reg, value: length } = &function.code[pc-1] else { continue; };
        if address != address_reg || value != value_reg || size != size_reg
            || address == value || address == size || value == size
            || entries[pc-2..=pc].iter().any(|entry| *entry)
            || *length > 512 { continue; }
        let length = *length as usize;
        if offset.checked_add(length).is_some_and(|end| end <= function.frame_size) {
            fills.insert(pc, LocalFill { offset: *offset, size: length, byte: *byte as u8 });
        }
    }
    fills
}

fn supported(op: &Op) -> bool {
    match op {
        Op::Imm { .. }
        | Op::Local { .. }
        | Op::Load { .. }
        | Op::Store { .. }
        | Op::Cast { .. }
        | Op::Select { .. }
        | Op::Assert { .. }
        | Op::CompareBytes { .. }
        | Op::Jump { .. } => true,
        // Keep code size and conditional-branch displacements bounded. Larger
        // switches retain the interpreter's complete u128 matching behavior.
        Op::Switch {cases,..} => cases.len() <= 16,
        Op::Copy { size, .. } => *size <= 128,
        Op::Binary { bits, op, .. } => *bits <= 64 || (*bits == 128 && matches!(op,
            Binary::Sub | Binary::Eq | Binary::Ne | Binary::Lt | Binary::Le
                | Binary::Gt | Binary::Ge | Binary::Cmp | Binary::And | Binary::Or
                | Binary::Xor | Binary::Shl | Binary::Shr)),
        Op::Unary { bits, .. } => *bits <= 64,
        _ => false,
    }
}

// Generated regions return small continuation indices on success. Faults use
// the high half: three fixed failures followed by per-assertion identities.
// Guest values never choose either kind of return code.
const FAILURE_MIN: u64 = 1 << 63;
const ASSERTION_FAILURE_BASE: u64 = u64::MAX - 3;
#[derive(Clone, Copy, PartialEq, Eq)]
#[repr(u64)]
enum Failure {
    Memory = u64::MAX,
    DivisionZero = u64::MAX - 1,
    DivisionOverflow = u64::MAX - 2,
}

#[derive(Clone, Copy)]
enum Fact {
    Imm(u128),
    Local(usize),
    Cached { lo: u32, high_zero: bool },
    Physical { lo: u32 },
}

#[derive(Default)]
struct Assembler<'a> {
    values: Option<&'a values::Allocation>,
    tree_caller_is_region: bool,
    resumable: bool,
    local_values: Vec<local_memory::Value>,
    #[cfg(test)]
    local_forwarding: Vec<(usize, &'static str)>,
    words: Vec<u32>,
    links: Vec<(usize, usize)>,
    failures: Vec<(usize, Failure)>,
    assertions: Vec<(usize, u64)>,
    heap: bool,
    frame_size: usize,
    reads: &'a [Option<(usize, usize)>],
    facts: BTreeMap<Reg, Fact>,
    defined: BTreeSet<Reg>,
    live_in: BTreeSet<Reg>,
    // x5/x6 are caller-saved and otherwise unused after heap relocation,
    // except for medium copies, which explicitly evict this local cache.
    // A narrow value occupies one slot; a wide value owns both slots.
    cached: [Option<Reg>; 2],
    cache_recent: usize,
    region_start: usize,
    region_end: usize,
    current_pc: usize,
}
impl Assembler<'_> {
    fn assertion(&mut self, value: Reg, expected: bool, code: u64) {
        // Bytecode truth is nonzero across all 128 bits, including values
        // produced by hand-built programs rather than Rust bool lowering.
        self.get(9, value, false);
        self.get(10, value, true);
        self.three(0xaa000000, 9, 9, 10); // orr x9,x9,x10
        self.cmp(9, 31);
        self.assertions.push((self.words.len(), code));
        self.emit(if expected { 0x54000000 } else { 0x54000001 }); // b.eq / b.ne failure
    }
    fn return_to_vm(&mut self) {
        if self.resumable {
            self.resumable_save_memory();
            self.resumable_save_budget();
        }
        self.restore_external_values();
        self.emit(0xd65f03c0);
    }
    fn return_pc(&mut self, pc: usize) {
        self.spill_values_at(pc);
        if self.resumable {
            self.resumable_save_pc(pc);
            self.mov(0, 31);
        } else { self.imm(0, pc as u64); }
        self.return_to_vm();
    }
    fn successor(&mut self, pc: usize) {
        self.links.push((self.words.len(), pc));
        self.emit(0x14000000); // patched b internal_entry / VM fallback
    }
    fn patch_conditional(&mut self, at: usize, target: usize) -> Result<(), EmitError> {
        // Forward local labels may be the next word to append. Only accept an
        // unpatched B.cond; bad indices/opcodes are emitter bugs, not declines.
        if at >= self.words.len() || target > self.words.len()
            || self.words[at] & !0xf != 0x54000000 {
            return Err(EmitError::InvalidRelocation("invalid JIT conditional relocation"));
        }
        self.words[at] |= branch_displacement(at, target, 19, CodegenLimit::ConditionalBranch)? << 5;
        Ok(())
    }
    fn exit(&mut self, terminal: Option<&Op>, fallthrough: usize) -> Result<(), EmitError> {
        match terminal {
            Some(Op::Jump {target}) => {
                self.successor(*target);
                Ok(())
            }
            Some(Op::Switch {value,cases,otherwise}) => {
                if let Some(Fact::Imm(value))=self.facts.get(value) {
                    let target=cases.iter().find(|(case,_)| case==value).map_or(*otherwise,|(_,target)| *target);
                    self.successor(target);
                    return Ok(());
                }
                if !cases.is_empty() {
                    self.get(9,*value,false);
                    self.get(10,*value,true);
                    // Compare both halves and retain first-match ordering,
                    // including when cases contain duplicate values.
                    for (case,target) in cases {
                        self.imm(11,*case as u64);
                        self.cmp(9,11);
                        let low=self.words.len();
                        self.emit(0x54000001); // b.ne next_case
                        self.imm(11,(*case>>64) as u64);
                        self.cmp(10,11);
                        let high=self.words.len();
                        self.emit(0x54000001);
                        self.successor(*target);
                        let next=self.words.len();
                        self.patch_conditional(low,next)?;
                        self.patch_conditional(high,next)?;
                    }
                }
                self.successor(*otherwise);
                Ok(())
            }
            None => {
                self.successor(fallthrough);
                Ok(())
            }
            _ => unreachable!("region exit is not a branch"),
        }
    }
    fn emit(&mut self, word: u32) {
        self.words.push(word);
    }
    fn imm(&mut self, rd: u32, value: u64) {
        self.emit(0xd2800000 | ((value as u32 & 0xffff) << 5) | rd); // movz
        for shift in 1..4 {
            let part = (value >> (shift * 16)) as u32 & 0xffff;
            if part != 0 {
                self.emit(0xf2800000 | (shift << 21) | (part << 5) | rd);
            }
        }
    }
    fn three(&mut self, opcode: u32, rd: u32, rn: u32, rm: u32) {
        self.emit(opcode | (rm << 16) | (rn << 5) | rd);
    }
    fn mov(&mut self, rd: u32, rn: u32) {
        self.three(0xaa000000, rd, 31, rn);
    }
    fn cmp(&mut self, a: u32, b: u32) {
        self.three(0xeb000000, 31, a, b);
    }
    fn cset(&mut self, rd: u32, condition: u32) {
        self.emit(0x9a9f07e0 | ((condition ^ 1) << 12) | rd);
    }
    // Inputs x9/x10 are masked to the guest width. Produce the wrapping result
    // in x9 and, when observed, the overflow boolean in x13. Capture flags
    // before spilling either output: guest source/result registers may alias.
    fn arithmetic(&mut self, op: Binary, bits: u8, signed: bool, observed: bool) {
        let plain = match op {
            Binary::Add => 0x8b000000,
            Binary::Sub => 0xcb000000,
            Binary::Mul => 0x9b007c00,
            _ => unreachable!(),
        };
        if !observed {
            self.three(plain, 9, 9, 10);
            return;
        }
        if bits < 64 {
            if signed { self.sign(9, bits); self.sign(10, bits); }
            // Two <=32-bit operands have an exact signed/unsigned product in
            // 64 bits. Unsigned subtraction may wrap 64 bits; its high set bits
            // still distinguish a borrow from a representable guest result.
            self.three(plain, 9, 9, 10);
            self.mov(11, 9);
            if signed { self.sign(11, bits); } else { self.mask(11, bits); }
            self.cmp(9, 11);
            self.cset(13, 1); // NE: narrowing changed the result
        } else if matches!(op, Binary::Mul) {
            self.three(if signed { 0x9b407c00 } else { 0x9bc07c00 }, 11, 9, 10); // SMULH/UMULH
            self.three(plain, 9, 9, 10);
            if signed {
                self.emit(0x9340fc00 | (63 << 16) | (9 << 5) | 12); // ASR x12,x9,#63
                self.cmp(11, 12); // high half must equal sign extension of low
            } else { self.cmp(11, 31); }
            self.cset(13, 1);
        } else {
            let add = matches!(op, Binary::Add);
            self.three(if add { 0xab000000 } else { 0xeb000000 }, 9, 9, 10); // ADDS/SUBS
            self.cset(13, if signed { 6 } else if add { 2 } else { 3 }); // VS/carry/borrow
        }
    }
    fn division(&mut self, op: Binary, bits: u8, signed: bool) {
        // Inputs are already masked to their guest width. Hardware division
        // returns zero for a zero divisor, so that condition needs an exit.
        self.cmp(10, 31);
        self.fail_with(0, Failure::DivisionZero);
        if signed {
            self.sign(9, bits);
            self.sign(10, bits);
            self.imm(11, 1u64 << (bits - 1));
            self.sign(11, bits);
            // (lhs ^ MIN) | !rhs is zero exactly for MIN / -1. Rust traps
            // for both division and remainder in that case.
            self.three(0xca000000, 11, 9, 11);
            self.three(0xaa200000, 12, 31, 10); // MVN x12,x10
            self.three(0xaa000000, 11, 11, 12);
            self.cmp(11, 31);
            self.fail_with(0, Failure::DivisionOverflow);
        }
        let opcode = if signed { 0x9ac00c00 } else { 0x9ac00800 }; // SDIV/UDIV
        if matches!(op, Binary::Rem) {
            self.three(opcode, 11, 9, 10);
            // MSUB x9,x11,x10,x9: lhs - quotient * rhs.
            self.emit(0x9b008000 | (10 << 16) | (9 << 10) | (11 << 5) | 9);
        } else {
            self.three(opcode, 9, 9, 10);
        }
    }
    fn wide_binary(&mut self, dst: Reg, overflow: Reg, op: Binary, a: Reg, b: Reg, signed: bool) {
        // Fetch both complete inputs before publishing either output. Sources,
        // result and overflow may alias in hand-built, validated bytecode.
        self.get(9, a, false);
        self.get(10, b, false);
        self.get(11, a, true);
        self.get(12, b, true);
        let observed = matches!(op, Binary::Sub) && self.reads[overflow as usize].is_some();
        match op {
            Binary::And | Binary::Or | Binary::Xor => {
                let opcode = match op {
                    Binary::And => 0x8a000000,
                    Binary::Or => 0xaa000000,
                    Binary::Xor => 0xca000000,
                    _ => unreachable!(),
                };
                self.three(opcode, 9, 9, 10);
                self.three(opcode, 11, 11, 12);
                self.put(dst, 9, 11);
            }
            Binary::Shl | Binary::Shr => {
                // Bytecode shifts mask the complete count modulo128. The low
                // seven bits suffice, regardless of the count's upper word.
                // A64 variable shifts mask modulo64; handle the cross-word
                // contribution at zero and select the >=64 result explicitly.
                self.mask(10, 7);
                self.three(0xcb000000, 12, 31, 10); // -count
                let left = matches!(op, Binary::Shl);
                self.three(if left { 0x9ac02400 } else { 0x9ac02000 },
                    13, if left { 9 } else { 11 }, 12);
                self.cmp(10, 31);
                self.emit(0x9a800000 | (13 << 16) | (31 << 5) | 13); // csel x13,xzr,x13,eq
                if left {
                    self.three(0x9ac02000, 11, 11, 10);
                    self.three(0xaa000000, 11, 11, 13);
                    self.three(0x9ac02000, 9, 9, 10);
                } else {
                    self.three(0x9ac02400, 9, 9, 10);
                    self.three(0xaa000000, 9, 9, 13);
                    self.three(if signed { 0x9ac02800 } else { 0x9ac02400 }, 11, 11, 10);
                    if signed {
                        self.emit(0x9340fc00 | (63 << 16) | (11 << 5) | 14); // asr x14,x11,#63
                    }
                }
                self.imm(12, 64);
                self.cmp(10, 12);
                if left {
                    self.emit(0x9a800000 | (11 << 16) | (2 << 12) | (9 << 5) | 11); // csel hi,lo,hi,hs
                    self.emit(0x9a800000 | (9 << 16) | (2 << 12) | (31 << 5) | 9); // csel lo,zr,lo,hs
                } else {
                    self.emit(0x9a800000 | (9 << 16) | (2 << 12) | (11 << 5) | 9); // csel lo,hi,lo,hs
                    self.emit(0x9a800000 | (11 << 16) | (2 << 12)
                        | ((if signed { 14 } else { 31 }) << 5) | 11); // csel hi,sign,hi,hs
                }
                self.put(dst, 9, 11);
            }
            Binary::Sub => {
                self.three(0xeb000000, 9, 9, 10); // SUBS low half, setting no-borrow
                self.three(if observed { 0xfa000000 } else { 0xda000000 }, 11, 11, 12); // SBCS/SBC high
                if observed { self.cset(13, if signed { 6 } else { 3 }); } // VS / borrow
                self.put(dst, 9, 11);
            }
            Binary::Eq | Binary::Ne => {
                self.three(0xca000000, 9, 9, 10);
                self.three(0xca000000, 11, 11, 12);
                self.three(0xaa000000, 9, 9, 11);
                self.cmp(9, 31);
                self.cset(9, u32::from(matches!(op, Binary::Ne)));
                self.put(dst, 9, 31);
            }
            Binary::Lt | Binary::Le | Binary::Gt | Binary::Ge | Binary::Cmp => {
                // Lexicographic comparison: only the high half is signed. If
                // it ties, use the unsigned low comparison, including for i128.
                let condition = |signed| match op {
                    Binary::Lt => if signed { 11 } else { 3 },
                    Binary::Le => if signed { 13 } else { 9 },
                    Binary::Gt | Binary::Cmp => if signed { 12 } else { 8 },
                    Binary::Ge => if signed { 10 } else { 2 },
                    _ => unreachable!(),
                };
                self.cmp(9, 10);
                self.cset(13, condition(false));
                if matches!(op, Binary::Cmp) {
                    self.cset(14, 3);
                    self.three(0xcb000000, 13, 13, 14);
                }
                self.cmp(11, 12);
                self.cset(9, condition(signed));
                if matches!(op, Binary::Cmp) {
                    self.cset(14, if signed { 11 } else { 3 });
                    self.three(0xcb000000, 9, 9, 14);
                }
                // CSET and non-flag-setting SUB preserve the high-half flags.
                self.emit(0x9a800000 | (9 << 16) | (13 << 5) | 9); // CSEL x9,x13,x9,EQ
                if matches!(op, Binary::Cmp) { self.mask(9, 8); }
                self.put(dst, 9, 31);
            }
            _ => unreachable!("unsupported wide binary operation"),
        }
        // Match the interpreter's value-then-overflow assignment order.
        self.put(overflow, if observed { 13 } else { 31 }, 31);
    }
    fn fail(&mut self, condition: u32) {
        self.fail_with(condition, Failure::Memory);
    }
    fn fail_with(&mut self, condition: u32, kind: Failure) {
        self.failures.push((self.words.len(), kind));
        self.emit(0x54000000 | condition);
    }
    fn mask(&mut self, rd: u32, bits: u8) {
        if bits < 64 {
            self.emit(0xd3400000 | ((u32::from(bits) - 1) << 10) | (rd << 5) | rd);
        } // ubfm #0,#bits-1
    }
    fn sign(&mut self, rd: u32, bits: u8) {
        if bits < 64 {
            self.emit(0x93400000 | ((u32::from(bits) - 1) << 10) | (rd << 5) | rd);
        }
    }
    fn reg_address(&mut self, reg: Reg, high: bool) -> (u32, u32) {
        let offset = u64::from(reg) * 16 + if high { 8 } else { 0 };
        if offset / 8 < 4096 {
            (0, (offset / 8) as u32)
        } else {
            self.imm(16, offset);
            self.three(0x8b000000, 16, 0, 16);
            (16, 0)
        }
    }
    fn get(&mut self, rd: u32, reg: Reg, high: bool) {
        if !self.defined.contains(&reg) { self.live_in.insert(reg); }
        if let Some(fact) = self.facts.get(&reg).copied() {
            self.materialize(rd, fact, high);
            return;
        }
        if let Some(lo) = self.assigned_pair(reg) {
            self.facts.insert(reg, Fact::Physical { lo });
            self.mov(rd, lo + u32::from(high));
            return;
        }
        let (base, offset) = self.reg_address(reg, high);
        self.emit(0xf9400000 | (offset << 10) | (base << 5) | rd);
    }
    fn put(&mut self, reg: Reg, lo: u32, hi: u32) {
        self.defined.insert(reg);
        self.facts.remove(&reg);
        self.forget_cached(reg);
        if self.reads[reg as usize].is_none() { return; }
        if let Some(physical) = self.assigned_pair(reg) {
            self.mov(physical, lo);
            self.mov(physical + 1, hi);
            self.facts.insert(reg, Fact::Physical { lo: physical });
            return;
        }
        if lo == 31 && hi == 31 {
            self.remember(reg, Fact::Imm(0));
            return;
        }
        let slot = if hi != 31 {
            self.evict_cached(false);
            self.mov(6, hi);
            self.cached[1] = Some(reg);
            0
        } else if let Some(slot) = self.cached.iter().position(Option::is_none) {
            slot
        } else {
            let slot = 1 - self.cache_recent;
            self.evict_cached_reg(self.cached[slot].unwrap(), false);
            slot
        };
        let physical = 5 + slot as u32;
        self.mov(physical, lo);
        self.facts.insert(reg, Fact::Cached { lo: physical, high_zero: hi == 31 });
        self.cached[slot] = Some(reg);
        self.cache_recent = slot;
    }
    fn forget_cached(&mut self, reg: Reg) {
        self.forget_local_register(reg);
        for owner in &mut self.cached {
            if *owner == Some(reg) { *owner = None; }
        }
    }
    fn evict_cached(&mut self, before_operands: bool) {
        for slot in 0..2 {
            if let Some(reg) = self.cached[slot] { self.evict_cached_reg(reg, before_operands); }
        }
    }
    fn evict_cached_reg(&mut self, reg: Reg, before_operands: bool) {
        self.forget_cached(reg);
        let Some(Fact::Cached { lo, high_zero }) = self.facts.remove(&reg) else {
            unreachable!("cache owner must have a dynamic fact");
        };
        let (first, last) = self.reads[reg as usize].expect("cached value is read");
        // A value may be used on another path, or at the next iteration's
        // entry. The same conservative bounds protect constant facts.
        let outside = first < self.region_start || last >= self.region_end || self.live_in.contains(&reg);
        let later = last > self.current_pc || (before_operands && last == self.current_pc);
        let needed = self.values.map_or(outside || later, |v|
            if before_operands { v.live.at(self.current_pc, reg) } else { v.live.after(self.current_pc, reg) });
        if needed { self.spill(reg, lo, if high_zero { 31 } else { 6 }); }
    }
    fn spill(&mut self, reg: Reg, lo: u32, hi: u32) {
        if let Some(physical) = self.assigned_pair(reg) {
            self.mov(physical, lo);
            self.mov(physical + 1, hi);
        } else { self.raw_spill(reg, lo, hi); }
    }
    fn raw_spill(&mut self, reg: Reg, lo: u32, hi: u32) {
        self.transfer_register_pair(false, reg, lo, hi);
    }
    fn transfer_register_pair(&mut self, load: bool, reg: Reg, lo: u32, hi: u32) {
        // Non-writeback LDP/STP has a signed seven-bit offset scaled by eight.
        // A VM register occupies sixteen initialized, host-owned bytes. Keep
        // two scalar accesses where a pair would need an extra address add;
        // for far registers, materialize their common base only once.
        if reg < 32 || reg >= 2048 {
            let (base, offset) = self.reg_address(reg, false);
            debug_assert!(offset < 64);
            self.emit((if load { 0xa9400000 } else { 0xa9000000 })
                | (offset << 15) | (hi << 10) | (base << 5) | lo);
            return;
        }
        for (high, rs) in [(false, lo), (true, hi)] {
            let (base, offset) = self.reg_address(reg, high);
            self.emit((if load { 0xf9400000 } else { 0xf9000000 })
                | (offset << 10) | (base << 5) | rs);
        }
    }
    fn remember(&mut self, reg: Reg, fact: Fact) {
        self.defined.insert(reg);
        self.forget_cached(reg);
        self.facts.remove(&reg);
        if self.reads[reg as usize].is_some() {
            self.facts.insert(reg, fact);
        }
    }
    fn materialize(&mut self, rd: u32, fact: Fact, high: bool) {
        match fact {
            Fact::Physical { lo } => self.mov(rd, lo + u32::from(high)),
            Fact::Cached { lo, high_zero } => {
                self.cache_recent = (lo - 5) as usize;
                self.mov(rd, if high { if high_zero { 31 } else { 6 } } else { lo });
            },
            Fact::Imm(value) => self.imm(rd, if high { (value >> 64) as u64 } else { value as u64 }),
            Fact::Local(_) if high => self.mov(rd, 31),
            Fact::Local(offset) => {
                if offset < 4096 {
                    self.emit(0x91000000 | ((offset as u32) << 10) | (1 << 5) | rd);
                } else {
                    self.imm(rd, offset as u64);
                    self.three(0x8b000000, rd, 1, rd);
                }
            }
        }
    }
    fn flush_facts(&mut self, start: usize, end: usize) {
        // Registers are not guest-addressable. A value used only inside this
        // straight-line region needs no spill. Conservatively retain every
        // value read elsewhere. Also retain values read before their first
        // definition in this region: a backedge may re-enter this same region
        // and read its previous execution's final value.
        let live: Vec<_> = self.facts.iter().filter_map(|(&reg, &fact)| {
            if matches!(fact, Fact::Physical { .. }) { return None; }
            if let Some(values) = self.values {
                return (values.live.at(end - 1, reg) || values.live.after(end - 1, reg)).then_some((reg, fact));
            }
            self.reads[reg as usize]
                .filter(|&(first, last)| matches!(fact, Fact::Cached { .. }) || first < start || last >= end || self.live_in.contains(&reg))
                .map(|_| (reg, fact))
        }).collect();
        for (reg, fact) in live {
            self.materialize(9, fact, false);
            self.materialize(10, fact, true);
            self.spill(reg, 9, 10);
        }
    }
    fn address(&mut self, rd: u32, reg: Reg, size: usize, write: bool) {
        if let Some(Fact::Local(offset)) = self.facts.get(&reg).copied() {
            if offset.checked_add(size).is_some_and(|end| end <= self.frame_size) {
                // The VM has allocated the complete active frame above the
                // read-only prefix. Supported regions cannot call or allocate,
                // so their frame storage cannot move or shrink during entry.
                self.materialize(rd, Fact::Local(offset), false);
                self.three(0x8b000000, rd, 2, rd);
                return;
            }
        }
        self.get(rd, reg, false);
        self.checked_address(rd, size, write);
    }
    fn fold(&mut self, op: &Op) -> bool {
        match *op {
            Op::Imm {dst, value} => self.remember(dst, Fact::Imm(value)),
            Op::Local {dst, offset} => self.remember(dst, Fact::Local(offset)),
            Op::Binary {dst, overflow, op, a, b, bits, signed} => {
                let left = self.facts.get(&a).copied();
                let right = self.facts.get(&b).copied();
                let folded = match (left, right) {
                    (Some(Fact::Imm(a)), Some(Fact::Imm(b))) => {
                        crate::binary(op, a, b, bits, signed).ok().map(|(value, overflow)| (Fact::Imm(value), overflow))
                    }
                    (Some(Fact::Local(offset)), Some(Fact::Imm(add)))
                    | (Some(Fact::Imm(add)), Some(Fact::Local(offset)))
                        if matches!(op, Binary::Add) && bits == 64 && !signed => {
                        // The bytecode masks integer operands to their width.
                        offset.checked_add(add as u64 as usize)
                            .filter(|&end| end <= self.frame_size)
                            .map(|end| (Fact::Local(end), false))
                    }
                    _ => None,
                };
                let Some((value, flag)) = folded else { return false; };
                self.remember(dst, value);
                self.remember(overflow, Fact::Imm(flag as u128));
            }
            _ => return false,
        }
        true
    }
    fn checked_address(&mut self, address: u32, size: usize, write: bool) {
        if size == 0 {
            // Nothing dereferences this address for a zero-byte operation.
            self.mov(address, 2);
            return;
        }
        if self.heap {
            self.imm(14, crate::heap::TAG as u64);
            self.cmp(address, 14);
            self.three(0xcb000000, 13, address, 14); // heap-relative offset
            // All four CSELs use the original unsigned address < heap tag.
            for (dst, stack, heap) in [(address, address, 13), (17, 2, 7), (15, 3, 8), (14, 4, 31)]
            {
                self.emit(0x9a800000 | (heap << 16) | (3 << 12) | (stack << 5) | dst);
            }
            self.cmp(address, 31);
            self.fail(0);
            self.cmp(address, 15);
            self.fail(8);
            self.three(0xcb000000, 15, 15, address);
            self.imm(13, size as u64);
            self.cmp(15, 13);
            self.fail(3);
            if write {
                self.cmp(address, 14);
                self.fail(3);
            }
            self.three(0x8b000000, address, 17, address);
            return;
        }
        // address and len comparisons avoid overflow in address+size. The
        // interpreter permits a null pointer only for zero-sized accesses.
        if size != 0 {
            self.cmp(address, 31);
            self.fail(0);
        }
        self.cmp(address, 3);
        self.fail(8); // hi: address > length
        self.three(0xcb000000, 15, 3, address);
        self.imm(14, size as u64);
        self.cmp(15, 14);
        self.fail(3); // lo: remaining < size
        if write && size != 0 {
            self.cmp(address, 4);
            self.fail(3);
        }
        self.three(0x8b000000, address, 2, address);
    }
    // Count is nonzero here. Check a complete read range without forming
    // address+count, which may overflow. Scratch x13/x14/x15/x17 leaves both
    // inputs, count, the x5/x6 value cache and the external ABI intact.
    fn dynamic_read_address(&mut self, address: u32, count: u32) {
        self.dynamic_address(address, count, false);
    }
    // As above, with readonly-prefix protection for a complete write range.
    // Both paths preserve x10/x11/x12 and the value cache except for `address`.
    fn dynamic_address(&mut self, address: u32, count: u32, write: bool) {
        if self.heap {
            self.imm(14, crate::heap::TAG as u64);
            self.cmp(address, 14);
            self.three(0xcb000000, 13, address, 14);
            for (dst, stack, heap) in [(address, address, 13), (17, 2, 7), (15, 3, 8)] {
                self.emit(0x9a800000 | (heap << 16) | (3 << 12) | (stack << 5) | dst);
            }
            if write {
                // Reuse the original tag comparison before changing flags.
                self.emit(0x9a800000 | (31 << 16) | (3 << 12) | (4 << 5) | 14);
            }
            self.cmp(address, 31);
            self.fail(0);
            self.cmp(address, 15);
            self.fail(8);
            self.three(0xcb000000, 15, 15, address);
            self.cmp(15, count);
            self.fail(3);
            if write {
                self.cmp(address, 14);
                self.fail(3);
            }
            self.three(0x8b000000, address, 17, address);
        } else {
            self.cmp(address, 31);
            self.fail(0);
            self.cmp(address, 3);
            self.fail(8);
            self.three(0xcb000000, 15, 3, address);
            self.cmp(15, count);
            self.fail(3);
            if write {
                self.cmp(address, 4);
                self.fail(3);
            }
            self.three(0x8b000000, address, 2, address);
        }
    }
    fn compare_bytes(&mut self, dst: Reg, left: Reg, right: Reg, size: Reg) {
        // All input registers are read before publishing the result, including
        // when dst aliases an address or count. usize truncation matches the VM.
        self.get(11, left, false);
        self.get(12, right, false);
        self.get(10, size, false);
        self.cmp(10, 31);
        let empty = self.words.len();
        self.emit(0x54000000); // b.eq equal (dangling empty ranges are valid)
        self.dynamic_read_address(11, 10);
        self.dynamic_read_address(12, 10);
        // Validate both complete ranges before inspecting even their first byte.
        // Unaligned eight-byte loads remain wholly inside the checked ranges.
        self.imm(14, 8);
        self.cmp(10, 14);
        let short = self.words.len();
        self.emit(0x54000003); // b.lo tail
        let wide_loop = self.words.len();
        self.emit(0xf9400000 | (11 << 5) | 9);
        self.emit(0xf9400000 | (12 << 5) | 13);
        self.cmp(9, 13);
        let wide_difference = self.words.len();
        self.emit(0x54000001); // b.ne wide_order
        for address in [11, 12] {
            self.emit(0x91000000 | (8 << 10) | (address << 5) | address);
        }
        self.emit(0xd1000000 | (8 << 10) | (10 << 5) | 10);
        self.cmp(10, 14);
        let more_wide = self.words.len();
        self.emit(0x54000002); // b.hs wide_loop
        let tail = self.words.len();
        self.cmp(10, 31);
        let exhausted = self.words.len();
        self.emit(0x54000000); // b.eq equal
        let byte_loop = self.words.len();
        self.emit(0x39400000 | (11 << 5) | 9);
        self.emit(0x39400000 | (12 << 5) | 13);
        self.cmp(9, 13);
        let byte_difference = self.words.len();
        self.emit(0x54000001); // b.ne ordered
        for address in [11, 12] {
            self.emit(0x91000000 | (1 << 10) | (address << 5) | address);
        }
        self.emit(0xf1000000 | (1 << 10) | (10 << 5) | 10); // subs count,#1
        let more_bytes = self.words.len();
        self.emit(0x54000001); // b.ne byte_loop
        let equal = self.words.len();
        self.mov(9, 31);
        let equal_done = self.words.len();
        self.emit(0x14000000); // b publish
        let wide_order = self.words.len();
        // Native words are little-endian: reverse before unsigned ordering so
        // the earliest differing byte determines the sign.
        for value in [9, 13] { self.emit(0xdac00c00 | (value << 5) | value); }
        self.cmp(9, 13);
        let ordered = self.words.len();
        self.cset(9, 8); // HI
        self.cset(13, 3); // LO; CSET preserves the comparison flags
        self.three(0xcb000000, 9, 9, 13);
        self.mask(9, 32); // VM encodes Less as u32::MAX, not u128::MAX
        let publish = self.words.len();
        for (at, target) in [(empty, equal), (short, tail), (wide_difference, wide_order),
            (more_wide, wide_loop), (exhausted, equal), (byte_difference, ordered),
            (more_bytes, byte_loop)] {
            self.patch_conditional(at, target).expect("bounded byte-compare branch");
        }
        // The publication sequence starts at the current end of the buffer;
        // the function-link helper requires an already emitted target. This
        // fixed local forward branch skips only the seven ordering words.
        assert_eq!(publish - equal_done, 8);
        self.words[equal_done] |= (publish - equal_done) as u32;
        self.put(dst, 9, 31);
    }

    fn load_mem(&mut self, lo: u32, hi: u32, base: u32, size: usize) {
        self.mov(lo, 31);
        self.mov(hi, 31);
        // Use byte assembly for unusual scalar widths (e.g. enum layouts).
        if [1, 2, 4, 8, 16].contains(&size) {
            let opcode = match size {
                1 => 0x39400000,
                2 => 0x79400000,
                4 => 0xb9400000,
                _ => 0xf9400000,
            };
            self.emit(opcode | (base << 5) | lo);
            if size == 16 {
                self.emit(0xf9400000 | (1 << 10) | (base << 5) | hi);
            }
        } else {
            for i in 0..size {
                self.emit(0x39400000 | ((i as u32) << 10) | (base << 5) | 13);
                self.emit(
                    0xaa000000
                        | (13 << 16)
                        | ((((i % 8) * 8) as u32) << 10)
                        | ((if i < 8 { lo } else { hi }) << 5)
                        | (if i < 8 { lo } else { hi }),
                );
            }
        }
    }
    fn store_mem(&mut self, lo: u32, hi: u32, base: u32, size: usize) {
        if [1, 2, 4, 8, 16].contains(&size) {
            let opcode = match size {
                1 => 0x39000000,
                2 => 0x79000000,
                4 => 0xb9000000,
                _ => 0xf9000000,
            };
            self.emit(opcode | (base << 5) | lo);
            if size == 16 {
                self.emit(0xf9000000 | (1 << 10) | (base << 5) | hi);
            }
        } else {
            for i in 0..size {
                let shift = ((i % 8) * 8) as u32;
                self.emit(0xd340fc00 | (shift << 16) | ((if i < 8 { lo } else { hi }) << 5) | 13); // lsr
                self.emit(0x39000000 | ((i as u32) << 10) | (base << 5) | 13);
            }
        }
    }
    fn local_fill(&mut self, fill: LocalFill) {
        self.invalidate_local_memory(Some(fill.offset), fill.size);
        // The entire writable range is within the allocated active frame.
        // No native operation can move its storage. These are plain byte
        // writes, matching FillBytes even for unaligned starts and short tails.
        if fill.size == 0 { return; }
        self.materialize(11, Fact::Local(fill.offset), false);
        self.three(0x8b000000, 11, 2, 11);
        let value = if fill.byte == 0 { 31 } else {
            self.imm(9, u64::from(fill.byte) * 0x0101_0101_0101_0101);
            9
        };
        let mut offset = 0usize;
        while fill.size - offset >= 16 {
            // stp value,value,[x11,#offset]; <=512 bytes keeps the signed
            // scaled displacement nonnegative and within its seven bits.
            self.emit(0xa9000000 | ((offset as u32 / 8) << 15)
                | (value << 10) | (11 << 5) | value);
            offset += 16;
        }
        for (width, opcode) in [(8,0xf9000000),(4,0xb9000000),(2,0x79000000),(1,0x39000000)] {
            if fill.size - offset >= width {
                self.emit(opcode | ((offset as u32 / width as u32) << 10) | (11 << 5) | value);
                offset += width;
            }
        }
        debug_assert_eq!(offset, fill.size);
    }

    fn lower(&mut self, op: &Op) {
        self.review_local_memory_effect(op);
        if self.fold(op) { return; }
        match *op {
            Op::Imm { dst, value } => {
                self.imm(9, value as u64);
                self.imm(10, (value >> 64) as u64);
                self.put(dst, 9, 10);
            }
            Op::Local { dst, offset } => {
                self.imm(9, offset as u64);
                self.three(0x8b000000, 9, 1, 9);
                self.put(dst, 9, 31);
            }
            Op::Load { dst, address, size } => {
                let local = self.local_range(address, size as usize);
                if let Some((_, value)) = self.local_value(local, size as usize) {
                    self.forward_local_value(value, size as usize, "Load");
                } else {
                    self.address(11, address, size as usize, false);
                    self.load_mem(9, 10, 11, size as usize);
                }
                self.put(dst, 9, if size <= 8 { 31 } else { 10 });
                self.remember_local_memory(local, size as usize, dst);
            }
            Op::Store { address, src, size } => {
                let local = self.local_range(address, size as usize);
                self.address(11, address, size as usize, true);
                self.get(9, src, false);
                self.get(10, src, true);
                self.store_mem(9, 10, 11, size as usize);
                self.invalidate_local_memory(local, size as usize);
                self.remember_local_memory(local, size as usize, src);
            }
            Op::CompareBytes { dst, left, right, size } => {
                self.compare_bytes(dst, left, right, size);
            }
            Op::Copy { dst, src, size } => {
                if (17..=32).contains(&size) { self.evict_cached(true); }
                let source_local = self.local_range(src, size);
                let destination_local = self.local_range(dst, size);
                let forwarded = self.local_value(source_local, size);
                if forwarded.is_none() { self.address(11, src, size, false); }
                self.address(12, dst, size, true);
                // Read all bytes before writing so even overlapping copies
                // preserve the interpreter's memmove behavior.
                if let Some((_, value)) = forwarded {
                    self.forward_local_value(value, size, "Copy");
                    self.store_mem(9, 31, 12, size);
                } else if size <= 16 {
                    self.load_mem(9, 10, 11, size);
                    self.store_mem(9, 10, 12, size);
                } else if size <= 32 {
                    self.load_mem(9, 10, 11, 16);
                    self.emit(0x91004000 | (11 << 5) | 11); // add x11,x11,#16
                    self.load_mem(5, 6, 11, size - 16);
                    self.store_mem(9, 10, 12, 16);
                    self.emit(0x91004000 | (12 << 5) | 12);
                    self.store_mem(5, 6, 12, size - 16);
                } else {
                    // Bounded memmove: v0..v7 are caller-saved and no other
                    // emitter operation keeps values in vector registers.
                    // Both complete ranges were validated above. Read every
                    // source byte before the first destination store.
                    let chunks = size / 16;
                    let tail = size % 16;
                    debug_assert!(chunks <= 8);
                    for chunk in 0..chunks as u32 {
                        self.emit(0x3dc00000 | (chunk << 10) | (11 << 5) | chunk); // ldr qN
                    }
                    if tail != 0 {
                        self.emit(0x91000000 | ((chunks as u32 * 16) << 10) | (11 << 5) | 11);
                        self.load_mem(9, 10, 11, tail);
                    }
                    for chunk in 0..chunks as u32 {
                        self.emit(0x3d800000 | (chunk << 10) | (12 << 5) | chunk); // str qN
                    }
                    if tail != 0 {
                        self.emit(0x91000000 | ((chunks as u32 * 16) << 10) | (12 << 5) | 12);
                        self.store_mem(9, 10, 12, tail);
                    }
                }
                self.invalidate_local_memory(destination_local, size);
                if let Some((source, _)) = forwarded {
                    self.remember_local_memory(destination_local, size, source);
                }
            }
            Op::Binary {
                dst,
                overflow,
                op,
                a,
                b,
                bits,
                signed,
            } => {
                if bits == 128 {
                    self.wide_binary(dst, overflow, op, a, b, signed);
                    return;
                }
                self.get(9, a, false);
                self.get(10, b, false);
                self.mask(9, bits);
                if !matches!(
                    op,
                    Binary::Shl | Binary::Shr | Binary::RotateLeft | Binary::RotateRight
                ) {
                    self.mask(10, bits);
                }
                let comparison = matches!(
                    op,
                    Binary::Eq
                        | Binary::Ne
                        | Binary::Lt
                        | Binary::Le
                        | Binary::Gt
                        | Binary::Ge
                        | Binary::Cmp
                );
                if comparison && signed {
                    self.sign(9, bits);
                    self.sign(10, bits);
                }
                let overflow_observed = matches!(op, Binary::Add | Binary::Sub | Binary::Mul)
                    && self.reads[overflow as usize].is_some();
                match op {
                    Binary::Add | Binary::Sub | Binary::Mul => self.arithmetic(op, bits, signed, overflow_observed),
                    Binary::Div | Binary::Rem => self.division(op, bits, signed),
                    Binary::And => self.three(0x8a000000, 9, 9, 10),
                    Binary::Or => self.three(0xaa000000, 9, 9, 10),
                    Binary::Xor => self.three(0xca000000, 9, 9, 10),
                    Binary::Shl | Binary::Shr | Binary::RotateLeft | Binary::RotateRight => {
                        self.imm(11, u64::from(bits) - 1);
                        self.three(0x8a000000, 10, 10, 11);
                        if matches!(op, Binary::Shr) && signed {
                            self.sign(9, bits);
                        }
                        match op {
                            Binary::Shl => self.three(0x9ac02000, 9, 9, 10),
                            Binary::Shr => {
                                self.three(if signed { 0x9ac02800 } else { 0x9ac02400 }, 9, 9, 10)
                            }
                            _ => {
                                if matches!(op, Binary::RotateLeft) {
                                    self.three(0xcb000000, 10, 31, 10);
                                }
                                if bits == 64 || bits == 32 {
                                    self.three(
                                        if bits == 64 { 0x9ac02c00 } else { 0x1ac02c00 },
                                        9,
                                        9,
                                        10,
                                    );
                                } else {
                                    self.three(0x8a000000, 10, 10, 11);
                                    self.three(0x9ac02400, 12, 9, 10);
                                    self.imm(11, u64::from(bits));
                                    self.three(0xcb000000, 10, 11, 10);
                                    self.three(0x9ac02000, 9, 9, 10);
                                    self.three(0xaa000000, 9, 9, 12);
                                }
                            }
                        }
                    }
                    _ => {
                        self.cmp(9, 10);
                        let cond = match op {
                            Binary::Eq => 0,
                            Binary::Ne => 1,
                            Binary::Lt => {
                                if signed {
                                    11
                                } else {
                                    3
                                }
                            }
                            Binary::Le => {
                                if signed {
                                    13
                                } else {
                                    9
                                }
                            }
                            Binary::Gt => {
                                if signed {
                                    12
                                } else {
                                    8
                                }
                            }
                            Binary::Ge => {
                                if signed {
                                    10
                                } else {
                                    2
                                }
                            }
                            Binary::Cmp => {
                                if signed {
                                    12
                                } else {
                                    8
                                }
                            }
                            _ => unreachable!(),
                        };
                        self.cset(9, cond);
                        if matches!(op, Binary::Cmp) {
                            self.cset(10, if signed { 11 } else { 3 });
                            self.three(0xcb000000, 9, 9, 10);
                            self.mask(9, 8);
                        }
                    }
                }
                self.mask(9, bits);
                self.put(dst, 9, 31);
                // The VM assigns the value first and overflow second, including
                // the unusual case where both name the same guest register.
                self.put(overflow, if overflow_observed { 13 } else { 31 }, 31);
            }
            Op::Unary { dst, op, src, bits } => {
                self.get(9, src, false);
                self.mask(9, bits);
                match op {
                    Unary::Not => self.three(0xaa200000, 9, 31, 9),
                    Unary::Neg => self.three(0xcb000000, 9, 31, 9),
                    Unary::SwapBytes => {
                        self.emit(0xdac00c00 | (9 << 5) | 9);
                        if bits < 64 {
                            self.emit(0xd340fc00 | ((64 - u32::from(bits)) << 16) | (9 << 5) | 9);
                        }
                    }
                    Unary::CountOnes => {
                        // x9 is already masked to the guest width. Count each
                        // byte, then sum at most eight counts (maximum 64).
                        // v0 is caller-saved and no operation keeps vector
                        // values live across another emitter operation.
                        self.emit(0x9e670120); // fmov d0, x9
                        self.emit(0x0e205800); // cnt v0.8b, v0.8b
                        self.emit(0x0e31b800); // addv b0, v0.8b
                        self.emit(0x0e013c09); // umov w9, v0.b[0]
                    }
                    Unary::LeadingZeros => {
                        self.emit(0xdac01000 | (9 << 5) | 9);
                        if bits < 64 {
                            self.imm(10, u64::from(64 - bits));
                            self.three(0xcb000000, 9, 9, 10);
                        }
                    }
                    Unary::TrailingZeros => {
                        self.emit(0xdac00000 | (9 << 5) | 9);
                        self.emit(0xdac01000 | (9 << 5) | 9);
                        if bits < 64 {
                            self.imm(10, u64::from(bits));
                            self.cmp(9, 10);
                            self.emit(0x9a800000 | (10 << 16) | (3 << 12) | (9 << 5) | 9);
                        }
                    }
                }
                self.mask(9, bits);
                self.put(dst, 9, 31);
            }
            Op::Cast {
                dst,
                src,
                from,
                to,
                signed,
            } => {
                self.get(9, src, false);
                self.get(10, src, true);
                if from < 128 {
                    self.mask(9, from);
                    if signed {
                        self.sign(9, from);
                        self.emit(0x9340fc00 | (63 << 16) | (9 << 5) | 10);
                    } else {
                        self.mov(10, 31);
                    }
                }
                if to < 128 {
                    self.mask(9, to);
                    self.mov(10, 31);
                }
                self.put(dst, 9, 10);
            }
            Op::Select {
                dst,
                condition,
                yes,
                no,
            } => {
                self.get(9, condition, false);
                self.get(10, condition, true);
                self.three(0xaa000000, 9, 9, 10);
                self.cmp(9, 31);
                self.get(9, yes, false);
                self.get(10, no, false);
                self.emit(0x9a800000 | (10 << 16) | (1 << 12) | (9 << 5) | 9);
                self.get(11, yes, true);
                self.get(12, no, true);
                self.emit(0x9a800000 | (12 << 16) | (1 << 12) | (11 << 5) | 10);
                self.put(dst, 9, 10);
            }
            _ => unreachable!(),
        }
    }
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod copy_tests;

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod popcount_tests;

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod wide_tests;

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod exit_tests;

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
#[path = "jit/lazy_tests.rs"]
mod lazy_tests;

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
#[path = "jit/register_cache_tests.rs"]
mod register_cache_tests;

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
#[path = "jit/compare_bytes_tests.rs"]
mod compare_bytes_tests;

#[path="jit/local_memory.rs"]
mod local_memory;
#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="jit/local_memory_tests.rs"]
mod local_memory_tests;


mod register_widths;
mod register_width_profile;
mod register_lifetimes;

/// Offline lifetime allocation diagnostic; the original program is unchanged.
pub fn register_lifetime_census(program: &Program, profile: Option<&[u8]>) -> Result<serde_json::Value, String> {
    register_lifetimes::census(program, profile)
}

/// Inspect a possible narrower register assignment without running guest code.
pub fn register_width_census(program: &Program) -> Result<serde_json::Value, String> {
    values::width_census(program, None)
}

/// Offline counts from a separately recorded, bytecode-verified execution profile.
pub fn register_width_profile_census(program: &Program, profile: &[u8]) -> Result<serde_json::Value, String> {
    values::width_census(program, Some(profile))
}

mod constant_arguments;

/// Offline argument-byte coverage; never changes or executes the program.
pub fn constant_call_argument_census(program: &Program, profile: Option<&[u8]>) -> Result<serde_json::Value, String> {
    constant_arguments::census(program, profile)
}
