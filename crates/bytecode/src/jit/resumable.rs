//! Direct Calls and Returns over initialized guest frames, with VM exits.
use super::*;
use crate::frames::{Frame, Frames, layout as frame};
use crate::native_continuation::{
    self as continuation, Boundary, Capacity, Exit, Run, State, Status,
};
use crate::{Limits, Memory};

// Live across every internal resumable edge. The external prologue saves
// the host value; every VM exit publishes the guest budget before restoring it.
// Guest persistent pairs remain x23/x24, x25/x26 and x27/x28.
pub(super) const BUDGET_REGISTER: u32 = 22;

const MAX_ENTRY_BYTES: usize = 16 * 1024 * 1024;
const SPARE_MEMORY: usize = 1024 * 1024;
const SPARE_REGISTERS: usize = 16 * 1024;
const SPARE_FRAMES: usize = 64;

/// Prove that the current memory end needs no callee alignment padding.
/// Returns retain earlier callees' pre-frame padding, so the memory end need
/// not equal the caller's original extent. If that extent is already aligned,
/// rounding it to any other validated power-of-two alignment preserves this
/// alignment: smaller alignments leave it alone and larger ones are multiples.
/// Otherwise padding depends on call history and needs the dynamic clear.
fn fixed_frame_clear_size(caller: &Function, callee: &Function) -> Option<usize> {
    if caller.frame_align < callee.frame_align
        || caller.frame_size.max(1) % callee.frame_align != 0 { return None; }
    let size = callee.frame_size.max(1);
    (size <= 256).then_some(size)
}

pub(super) struct Entries {
    owned: Vec<Vec<usize>>,
    pointers: Vec<*const usize>,
    bytes: usize,
    pub zeroes: Vec<bool>,
}
// Test-only byte ownership: these labels emit no instructions and never enter
// the production VM or its artifact/code-map formats.
#[cfg(test)]
#[derive(Debug, serde::Serialize)]
pub(super) struct ProtocolSpan {
    pub offset: usize,
    pub end: usize,
    pub kind: &'static str,
    pub argument: Option<usize>,
}

macro_rules! protocol_mark {
    ($a:expr, $kind:literal, $argument:expr) => {
        #[cfg(test)]
        $a.mark_protocol($kind, $argument);
    };
}

#[cfg(test)]
impl Assembler<'_> {
    fn mark_protocol(&mut self, kind: &'static str, argument: Option<usize>) {
        let offset = self.protocol_spans.last().map_or(0, |s| s.end);
        let end = self.words.len() * 4;
        assert!(offset <= end);
        if offset < end {
            self.protocol_spans.push(ProtocolSpan { offset, end, kind, argument });
        }
    }
}

impl Entries {
    fn new(program: &Program) -> Self {
        Self {
            owned: vec![vec![]; program.functions.len()],
            pointers: vec![std::ptr::null(); program.functions.len()],
            bytes: 0,
            zeroes: program
                .functions
                .iter()
                .map(crate::registers::needs_initial_zeroes)
                .collect(),
        }
    }
    pub fn fits(&self, code_len: usize) -> bool {
        code_len
            .checked_add(1)
            .and_then(|n| n.checked_mul(8))
            .is_some_and(|n| n <= MAX_ENTRY_BYTES - self.bytes)
    }
    pub fn publish(&mut self, id: usize, entries: Vec<usize>) {
        debug_assert!(self.pointers[id].is_null());
        self.bytes += entries.len() * 8;
        self.owned[id] = entries;
        self.pointers[id] = self.owned[id].as_ptr();
    }
    pub(super) fn published(&self, id: usize) -> &[usize] { &self.owned[id] }
}

#[repr(C)]
struct ResumeCursor {
    state: State,
    frames: *mut Frame,
    registers: *mut u128,
    entries: *const *const usize,
    profiles: *const *mut u64,
    memory_end: usize,
    register_end: usize,
    // Effective backing/logical depth bound, fixed before native execution.
    frame_end: usize,
    working_budget: usize,
}

use continuation::layout as state;
const FRAMES: usize = std::mem::offset_of!(ResumeCursor, frames);
const REGISTERS: usize = std::mem::offset_of!(ResumeCursor, registers);
const ENTRIES: usize = std::mem::offset_of!(ResumeCursor, entries);
const PROFILES: usize = std::mem::offset_of!(ResumeCursor, profiles);
const MEMORY_END: usize = std::mem::offset_of!(ResumeCursor, memory_end);
const REGISTER_END: usize = std::mem::offset_of!(ResumeCursor, register_end);
const FRAME_END: usize = std::mem::offset_of!(ResumeCursor, frame_end);
const WORKING_BUDGET: usize = std::mem::offset_of!(ResumeCursor, working_budget);
const _: () = {
    assert!(std::mem::offset_of!(ResumeCursor, state) == 0);
};
#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
const _: () = {
    assert!(state::REMAINING == std::mem::offset_of!(Cursor, remaining));
    assert!(state::PROFILE_HITS == std::mem::offset_of!(Cursor, profile_hits));
    assert!(FRAMES == 64 && REGISTERS == 72 && ENTRIES == 80 && PROFILES == 88);
    assert!(MEMORY_END == 96 && REGISTER_END == 104 && FRAME_END == 112);
    assert!(WORKING_BUDGET == 120);
    assert!(std::mem::size_of::<ResumeCursor>() == 128);
};

impl<'a> Jit<'a> {
    pub(crate) fn new_resumable(
        program: &'a Program,
        profiled: bool,
        capacity: usize,
        persistent: bool,
    ) -> Result<Self, String> {
        let mut jit = Self::new_with_options(program, profiled, capacity, false, persistent)?;
        jit.resumable = Some(Entries::new(program));
        Ok(jit)
    }

    pub(crate) fn resumable_register_zeroes(&self) -> &[bool] {
        &self.resumable.as_ref().unwrap().zeroes
    }

    /// Run prepared native regions, possibly switching guest frames.
    ///
    /// # Safety
    /// The program was validated before constructing this JIT. This execution
    /// exclusively owns all initialized guest storage and descriptors; their
    /// active prefix is a valid VM stack. A profiled entry supplies one stable
    /// initialized counter array per function, of that function's code length.
    /// No live borrowed Frame/register/memory slice overlaps generated writes.
    /// This synchronous call runs on the JIT's owning thread, with no concurrent
    /// allocation, publication, metadata mutation or write-protection change.
    pub(crate) unsafe fn run_resumable(
        &self,
        block: Block,
        budget: u64,
        limits: &Limits,
        memory: &mut Memory,
        registers: &mut Vec<u128>,
        frames: &mut Frames,
        register_bytes: &mut usize,
        profiles: &[*mut u64],
    ) -> Result<Run, String> {
        let entry = *frames.last().ok_or("missing resumable entry frame")?;
        if !self.blocks[entry.function]
            .get(entry.pc)
            .copied()
            .flatten()
            .is_some_and(|b| b.offset == block.offset && b.end == block.end)
        {
            return Err("invalid resumable native entry".into());
        }
        let fixed = memory
            .heap
            .bytes
            .len()
            .checked_add(memory.auxiliary_bytes)
            .ok_or("native fixed memory overflow")?;
        let working_budget = limits
            .memory
            .checked_sub(fixed)
            .ok_or("invalid native fixed memory")?;
        let wanted = memory
            .bytes
            .len()
            .saturating_add(SPARE_MEMORY)
            .min(working_budget);
        let memory_end = if memory.bytes.prepare(wanted).is_ok() {
            wanted
        } else {
            memory.bytes.len()
        };
        let wanted = (*register_bytes / 16)
            .saturating_add(SPARE_REGISTERS)
            .min(working_budget / 16);
        if wanted > registers.len() && registers.try_reserve(wanted - registers.len()).is_ok() {
            registers.resize(wanted, 0);
        }
        let register_end = wanted.min(registers.len());
        let wanted = frames.len().saturating_add(SPARE_FRAMES).min(limits.frames);
        let frame_end = if frames.prepare(wanted).is_ok() {
            wanted
        } else {
            frames.len()
        };
        let hits = if self.profiled {
            if profiles.len() != self.program.functions.len() {
                return Err("invalid native profile table".into());
            }
            profiles[entry.function]
        } else {
            std::ptr::null_mut()
        };
        let boundary = Boundary::new(
            self.program,
            memory,
            registers,
            frames,
            *register_bytes,
            budget,
            limits,
            Capacity {
                memory: memory_end,
                registers: register_end,
                frames: frame_end,
            },
            hits,
        )?;
        let mut cursor = ResumeCursor {
            state: boundary.state(),
            frames: frames.prepared_mut_ptr(),
            registers: registers.as_mut_ptr(),
            entries: self.resumable.as_ref().unwrap().pointers.as_ptr(),
            profiles: profiles.as_ptr(),
            memory_end,
            register_end,
            frame_end: frame_end.min(limits.frames),
            working_budget,
        };
        // SAFETY: all preparation precedes these fresh exclusive pointers.
        // Native guards bound every push, zero/copy and profile/table access.
        // No Rust storage method or lazy compilation runs until it returns.
        let code = unsafe {
            self.code.as_ref().ok_or("missing resumable code")?.call(
                block.offset,
                registers.as_mut_ptr().add(entry.register_base),
                entry.base,
                memory.bytes.prepared_mut_ptr(),
                memory.bytes.len(),
                memory.readonly_end,
                memory.heap.bytes.as_mut_ptr(),
                memory.heap.bytes.len(),
                std::ptr::addr_of_mut!(cursor).cast::<Cursor>(),
            )
        };
        let status = if code == 0 {
            Status::Continue
        } else if code >= FAILURE_MIN {
            Status::Fault(code)
        } else {
            return Err("invalid resumable native status".into());
        };
        let run = boundary.finish(
            self.program,
            memory,
            registers,
            frames,
            register_bytes,
            cursor.state,
            status,
        )?;
        if let Exit::Fault(code) = run.exit {
            return Err(self.fault_message(code)?);
        }
        Ok(run)
    }

    pub(super) fn emit_resumable_transition<'b>(
        &self,
        f: &Function,
        pc: usize,
        reads: &'b [Option<(usize, usize)>],
        values: Option<&'b values::Allocation>,
        slots: Option<&[Option<usize>]>,
    ) -> Result<(Assembler<'b>, usize, usize), EmitError> {
        let mut a = Assembler {
            heap: self.uses_heap,
            reads,
            values,
            resumable: true,
            #[cfg(test)]
            register_native_counters: self.register_native_counters,
            frame_size: f.frame_size,
            current_pc: pc,
            region_start: pc,
            region_end: pc + 1,
            ..Assembler::default()
        };
        let resume = a.external_entry();
        protocol_mark!(a, "entry", None);
        let internal = a.words.len();
        let mut declines = vec![];
        a.cmp(BUDGET_REGISTER, 31);
        a.decline(Cond::Eq, &mut declines);
        protocol_mark!(a, "entry_budget", None);
        match &f.code[pc] {
            Op::Call {
                function,
                args,
                destination,
            } => {
                let callee = &self.program.functions[*function];
                a.resumable_call(
                    f,
                    pc,
                    *function,
                    callee,
                    args,
                    slots,
                    *destination,
                    self.resumable.as_ref().unwrap().zeroes[*function],
                    self.profiled,
                    &mut declines,
                )?;
            }
            Op::Return => a.resumable_return(f, pc, self.profiled, &mut declines)?,
            _ => return Err(EmitError::InvalidRelocation("invalid resumable transition")),
        }
        let failures = std::mem::take(&mut a.failures);
        for kind in [
            Failure::Memory,
            Failure::DivisionZero,
            Failure::DivisionOverflow,
        ] {
            if !failures.iter().any(|&(_, k)| k == kind) {
                continue;
            }
            let target = a.words.len();
            a.imm(0, kind as u64);
            a.return_to_vm();
            for &(at, k) in &failures {
                if k == kind {
                    a.patch_conditional(at, target)?;
                }
            }
        }
        protocol_mark!(a, "fault_tail", None);
        let target = a.words.len();
        a.return_pc(pc);
        for at in declines {
            a.patch_conditional(at, target)?;
        }
        protocol_mark!(a, "admission_fallback", None);
        Ok((a, resume, internal))
    }
}

#[derive(Clone, Copy)]
pub(super) enum Cond {
    Eq = 0,
    Ne = 1,
    Hs = 2,
    Lo = 3,
    Hi = 8,
    Ls = 9,
}

impl Assembler<'_> {
    fn load64(&mut self, rd: u32, base: u32, offset: usize) {
        assert!(offset % 8 == 0 && offset / 8 < 4096);
        self.emit(0xf9400000 | ((offset as u32 / 8) << 10) | (base << 5) | rd);
    }
    fn store64(&mut self, src: u32, base: u32, offset: usize) {
        assert!(offset % 8 == 0 && offset / 8 < 4096);
        self.emit(0xf9000000 | ((offset as u32 / 8) << 10) | (base << 5) | src);
    }
    fn lsl_imm(&mut self, dst: u32, src: u32, shift: u32) {
        assert!(shift > 0 && shift < 64);
        self.emit(0xd3400000 | ((64 - shift) << 16) | ((63 - shift) << 10) | (src << 5) | dst);
    }
    fn add_imm(&mut self, dst: u32, src: u32, immediate: usize) {
        assert!(immediate < 4096);
        self.emit(0x91000000 | ((immediate as u32) << 10) | (src << 5) | dst);
    }
    pub(super) fn sub_imm(&mut self, dst: u32, src: u32, immediate: usize) {
        assert!(immediate < 4096);
        self.emit(0xd1000000 | ((immediate as u32) << 10) | (src << 5) | dst);
    }
    fn decline(&mut self, condition: Cond, declines: &mut Vec<usize>) {
        declines.push(self.words.len());
        self.emit(0x54000000 | condition as u32);
    }
    fn increment_cursor(&mut self, field: usize) {
        if self.increment_native_counter(field) { return; }
        self.load64(9, 19, field);
        self.add_imm(9, 9, 1);
        self.store64(9, 19, field);
    }
    fn charge_transition(&mut self, pc: usize, profiled: bool) {
        self.sub_imm(BUDGET_REGISTER, BUDGET_REGISTER, 1);
        protocol_mark!(self, "charge_budget", None);
        if profiled {
            self.load64(10, 19, state::PROFILE_HITS);
            self.imm(11, pc as u64 * 8);
            self.three(0x8b000000, 10, 10, 11);
            self.load64(11, 10, 0);
            self.add_imm(11, 11, 1);
            self.store64(11, 10, 0);
        }
    }
    pub(super) fn resumable_save_host(&mut self, load: bool) {
        if !load {
            self.push_pair(19, 30, 96);
        }
        for (a, b, offset) in [
            (20, 21, 16),
            (22, 31, 32),
            (23, 24, 48),
            (25, 26, 64),
            (27, 28, 80),
        ] {
            self.stack_pair(load, a, b, offset);
        }
        if load {
            self.pop_pair(19, 30, 96);
        }
    }
    pub(super) fn resumable_current_frame(&mut self) {
        self.load64(9, 19, state::FRAME_LEN);
        self.sub_imm(9, 9, 1);
        self.imm(10, frame::SIZE as u64);
        self.three(0x9b007c00, 9, 9, 10); // mul x9,x9,x10
        self.load64(20, 19, FRAMES);
        self.three(0x8b000000, 20, 20, 9);
    }
    pub(super) fn resumable_load_budget(&mut self) {
        self.load64(BUDGET_REGISTER, 19, state::REMAINING);
    }
    pub(super) fn resumable_save_budget(&mut self) {
        self.store64(BUDGET_REGISTER, 19, state::REMAINING);
    }
    pub(super) fn resumable_save_memory(&mut self) {
        self.store64(3, 19, state::MEMORY_LEN);
    }
    pub(super) fn resumable_save_pc(&mut self, pc: usize) {
        self.imm(9, pc as u64);
        self.store64(9, 20, frame::PC);
    }
    fn callee_target(&mut self, id: usize, declines: Option<&mut Vec<usize>>) {
        self.load64(9, 19, ENTRIES);
        self.imm(10, id as u64 * 8);
        self.three(0x8b000000, 9, 9, 10);
        self.load64(9, 9, 0);
        if let Some(declines) = declines {
            self.cmp(9, 31);
            self.decline(Cond::Eq, declines);
            self.load64(16, 9, 0);
            self.cmp(16, 31);
            self.decline(Cond::Eq, declines);
        } else {
            self.load64(16, 9, 0);
        }
    }
    fn switch_profile(&mut self, profiled: bool) {
        if profiled {
            self.load64(9, 20, frame::FUNCTION);
            self.lsl_imm(9, 9, 3);
            self.load64(10, 19, PROFILES);
            self.three(0x8b000000, 9, 10, 9);
            self.load64(9, 9, 0);
            self.store64(9, 19, state::PROFILE_HITS);
        }
    }

    /// Clear the prechecked host range [x11,x12), whose length is at least
    /// `minimum`. Only the old zero_range scratch registers are clobbered.
    /// Plain pair stores permit unaligned normal memory and never extend past
    /// x12. A known 64-byte minimum permits the first batch without a guard;
    /// subsequent batches test the remaining length. The old helper handles
    /// the exact tail, including empty ranges. Small frames emit no extra test.
    fn zero_range_at_least(&mut self, minimum: usize) -> Result<(), EmitError> {
        const BATCH: usize = 64;
        if minimum >= BATCH {
            self.three(0xcb000000, 9, 12, 11);
            self.imm(10, BATCH as u64);
            let batch = self.words.len();
            for offset in (0..BATCH).step_by(16) {
                // stp xzr,xzr,[x11,#offset]; offsets fit signed scaled imm7.
                self.emit(0xa9000000 | ((offset as u32 / 8) << 15) | (31 << 10) | (11 << 5) | 31);
            }
            self.add_imm(11, 11, BATCH);
            self.sub_imm(9, 9, BATCH);
            self.cmp(9, 10);
            let more = self.words.len();
            self.emit(0x54000000 | Cond::Hs as u32);
            self.patch_conditional(more, batch)?;
        }
        self.zero_range()
    }

    /// Hints never replace runtime register state. Equality with a proved
    /// current-frame range permits direct host addressing; mismatch follows
    /// the original check after the same charge, clearing and earlier copies.
    fn call_argument_address(&mut self, source: Reg, size: usize, hint: Option<usize>) -> Result<(), EmitError> {
        let Some(offset) = hint.filter(|&offset| size != 0 && offset.checked_add(size)
            .is_some_and(|end| end <= self.frame_size)) else {
            self.address(11, source, size, false);
            return Ok(());
        };
        self.get(11, source, false); // including persistent pairs / large offsets
        self.imm(12, offset as u64);
        self.three(0x8b000000, 12, 1, 12); // expected guest address, not a host pointer
        self.cmp(11, 12);
        let fast = self.words.len();
        self.emit(0x54000000 | Cond::Eq as u32);
        self.checked_address(11, size, false);
        let done = self.words.len();
        self.emit(0x14000000);
        self.patch_conditional(fast, self.words.len())?;
        self.three(0x8b000000, 11, 2, 12);
        // This local target is the next instruction appended by the caller.
        // The branch slot was emitted immediately above and has no other owner.
        self.words[done] |= branch_displacement(done, self.words.len(), 26, CodegenLimit::Jump)?;
        Ok(())
    }

    /// Clear an exact prechecked range beginning at x11. The caller proves
    /// the length, including alignment padding. No access extends past it.
    fn zero_fixed(&mut self, size: usize) {
        assert!(size <= 256);
        let pairs = size / 16 * 16;
        for offset in (0..pairs).step_by(16) {
            self.emit(0xa9000000 | ((offset as u32 / 8) << 15) | (31 << 10) | (11 << 5) | 31);
        }
        let mut offset = pairs;
        for (width, opcode) in [(8, 0xf9000000), (4, 0xb9000000), (2, 0x79000000), (1, 0x39000000)] {
            if size - offset >= width {
                self.emit(opcode | ((offset as u32 / width as u32) << 10) | (11 << 5) | 31);
                offset += width;
            }
        }
        debug_assert_eq!(offset, size);
    }

    /// x11/x12 delimit the complete prechecked clear, including actual padding;
    /// x21 is the callee's guest base and x2 is the stable host memory base.
    /// Small payloads can use fixed stores even when padding depends on call
    /// history: first clear that exact dynamic prefix, then the fixed payload.
    /// Preserve x16 (callee target), x17 (register cursor), and x22 (budget).
    fn clear_call_frame(&mut self, caller: &Function, callee: &Function) -> Result<(), EmitError> {
        if let Some(size) = fixed_frame_clear_size(caller, callee) {
            self.zero_fixed(size);
        } else if callee.frame_size.max(1) <= 256 {
            self.three(0x8b000000, 12, 2, 21);
            self.cmp(11, 12);
            let empty = self.words.len();
            self.emit(0x54000000 | Cond::Eq as u32);
            self.zero_range()?;
            self.patch_conditional(empty, self.words.len())?;
            // zero_range leaves x11 at the end of the padding on both paths.
            self.zero_fixed(callee.frame_size.max(1));
        } else {
            self.zero_range_at_least(callee.frame_size.max(1))?;
        }
        Ok(())
    }

    fn resumable_call(
        &mut self,
        caller: &Function,
        pc: usize,
        id: usize,
        callee: &Function,
        args: &[Reg],
        slots: Option<&[Option<usize>]>,
        destination: Reg,
        zeroes: bool,
        profiled: bool,
        declines: &mut Vec<usize>,
    ) -> Result<(), EmitError> {
        self.callee_target(id, Some(&mut *declines));
        protocol_mark!(self, "call_target", None);
        self.load64(9, 19, state::FRAME_LEN);
        self.load64(10, 19, FRAME_END);
        self.cmp(9, 10);
        self.decline(Cond::Hs, declines);
        protocol_mark!(self, "call_frame_capacity", None);
        self.imm(10, callee.frame_align as u64 - 1);
        self.three(0xab000000, 21, 3, 10); // adds; carry means alignment overflow
        self.decline(Cond::Hs, declines);
        self.imm(10, !(callee.frame_align as u64 - 1));
        self.three(0x8a000000, 21, 21, 10);
        self.imm(10, callee.frame_size.max(1) as u64);
        self.three(0xab000000, 11, 21, 10);
        self.decline(Cond::Hs, declines);
        self.load64(10, 19, MEMORY_END);
        self.cmp(11, 10);
        self.decline(Cond::Hi, declines);
        protocol_mark!(self, "call_memory_capacity", None);
        self.load64(12, 19, state::REGISTER_LEN);
        self.imm(10, callee.registers as u64);
        self.three(0xab000000, 17, 12, 10);
        self.decline(Cond::Hs, declines);
        self.load64(10, 19, REGISTER_END);
        self.cmp(17, 10);
        self.decline(Cond::Hi, declines);
        protocol_mark!(self, "call_register_capacity", None);
        // The register bound is the length of an initialized Vec<u128>, so
        // multiplying a bounded slot count by 16 cannot overflow.
        self.lsl_imm(13, 17, 4);
        self.three(0xab000000, 13, 13, 11);
        self.decline(Cond::Hs, declines);
        self.load64(10, 19, WORKING_BUDGET);
        self.cmp(13, 10);
        self.decline(Cond::Hi, declines);

        protocol_mark!(self, "call_working_budget", None);
        self.charge_transition(pc, profiled);
        protocol_mark!(self, "charge_profile", None);
        self.spill_values_at(pc + 1);
        protocol_mark!(self, "call_spill", None);
        self.three(0x8b000000, 11, 2, 3);
        self.imm(9, callee.frame_size.max(1) as u64);
        self.three(0x8b000000, 3, 21, 9);
        self.three(0x8b000000, 12, 2, 3);
        self.clear_call_frame(caller, callee)?;
        protocol_mark!(self, "call_frame_clear", None);
        self.load64(9, 19, state::PEAK_LINEAR);
        self.cmp(3, 9);
        self.emit(0x9a892069); // csel x9,x3,x9,hs
        self.store64(9, 19, state::PEAK_LINEAR);
        protocol_mark!(self, "call_peak_memory", None);
        for (index, (source, slot)) in args.iter().zip(&callee.args).enumerate() {
            self.call_argument_address(*source, slot.size, slots.and_then(|s| s.get(index).copied()).flatten())?;
            protocol_mark!(self, "argument_source", Some(index));
            self.imm(12, slot.offset as u64);
            self.three(0x8b000000, 12, 21, 12);
            self.three(0x8b000000, 12, 2, 12);
            protocol_mark!(self, "argument_destination", Some(index));
            self.abi_copy(slot.size)?;
            protocol_mark!(self, "argument_copy", Some(index));
        }
        self.imm(9, caller.registers as u64 * 16);
        self.three(0x8b000000, 17, 0, 9);
        protocol_mark!(self, "call_register_cursor", None);
        if zeroes {
            self.mov(11, 17);
            self.imm(12, callee.registers as u64 * 16);
            self.three(0x8b000000, 12, 17, 12);
            self.zero_range_at_least(callee.registers as usize * 16)?;
        }
        protocol_mark!(self, "call_register_clear", None);
        self.get(15, destination, false);
        protocol_mark!(self, "call_result_pointer", None);
        self.resumable_save_pc(pc + 1);
        self.add_imm(20, 20, frame::SIZE);
        self.imm(9, id as u64);
        self.store64(9, 20, frame::FUNCTION);
        self.store64(31, 20, frame::PC);
        self.store64(21, 20, frame::BASE);
        self.load64(9, 19, state::REGISTER_LEN);
        self.store64(9, 20, frame::REGISTER_BASE);
        self.store64(15, 20, frame::RETURN_ADDRESS);
        self.emit(0x39000000 | ((frame::TLS_CALLBACK as u32) << 10) | (20 << 5) | 31);
        self.imm(10, callee.registers as u64);
        self.three(0x8b000000, 9, 9, 10);
        self.store64(9, 19, state::REGISTER_LEN);
        self.increment_cursor(state::FRAME_LEN);
        self.increment_cursor(state::CALLS);
        self.mov(0, 17);
        self.mov(1, 21);
        protocol_mark!(self, "call_publish_frame", None);
        self.switch_profile(profiled);
        protocol_mark!(self, "profile_switch", None);
        // reg_address uses x16 only beyond its scaled imm12 range. Both
        // halves of all validated caller registers fit when there are <=2048
        // slots. Other successful call helpers preserve x16; larger callers
        // retain the reload after argument/result access and live-value spills.
        if caller.registers > 2048 { self.callee_target(id, None); }
        self.emit(0xd61f0200); // br x16, no host-stack recursion
        protocol_mark!(self, "call_dispatch", None);
        Ok(())
    }

    fn resumable_return(
        &mut self,
        f: &Function,
        pc: usize,
        profiled: bool,
        declines: &mut Vec<usize>,
    ) -> Result<(), EmitError> {
        self.load64(9, 19, state::FRAME_LEN);
        self.imm(10, 1);
        self.cmp(9, 10);
        self.decline(Cond::Ls, declines);
        self.emit(0x39400000 | ((frame::TLS_CALLBACK as u32) << 10) | (20 << 5) | 9);
        self.cmp(9, 31);
        self.decline(Cond::Ne, declines);
        protocol_mark!(self, "return_admission", None);
        self.charge_transition(pc, profiled);
        protocol_mark!(self, "charge_profile", None);
        self.mov(21, 1);
        self.imm(11, f.result.offset as u64);
        self.three(0x8b000000, 11, 1, 11);
        self.three(0x8b000000, 11, 2, 11);
        protocol_mark!(self, "result_source", None);
        self.load64(12, 20, frame::RETURN_ADDRESS);
        self.checked_address(12, f.result.size, true);
        protocol_mark!(self, "result_destination", None);
        self.abi_copy(f.result.size)?;
        protocol_mark!(self, "result_copy", None);
        self.mov(3, 21);
        // The checked result copy can clobber x17. Frame metadata is private
        // host storage and unchanged by that copy; read it only after success.
        self.load64(17, 20, frame::REGISTER_BASE);
        self.store64(17, 19, state::REGISTER_LEN);
        self.load64(9, 19, state::FRAME_LEN);
        self.sub_imm(9, 9, 1);
        self.store64(9, 19, state::FRAME_LEN);
        self.increment_cursor(state::RETURNS);
        self.sub_imm(20, 20, frame::SIZE);
        self.load64(9, 20, frame::REGISTER_BASE);
        self.lsl_imm(9, 9, 4);
        self.load64(0, 19, REGISTERS);
        self.three(0x8b000000, 0, 0, 9);
        self.load64(1, 20, frame::BASE);
        protocol_mark!(self, "return_restore_frame", None);
        self.switch_profile(profiled);
        protocol_mark!(self, "profile_switch", None);
        self.load64(9, 20, frame::FUNCTION);
        self.lsl_imm(9, 9, 3);
        self.load64(10, 19, ENTRIES);
        self.three(0x8b000000, 9, 10, 9);
        self.load64(9, 9, 0);
        self.cmp(9, 31);
        let mut vm = vec![];
        self.decline(Cond::Eq, &mut vm);
        self.load64(10, 20, frame::PC);
        self.lsl_imm(10, 10, 3);
        self.three(0x8b000000, 9, 9, 10);
        self.load64(16, 9, 0);
        self.cmp(16, 31);
        self.decline(Cond::Eq, &mut vm);
        self.emit(0xd61f0200);
        protocol_mark!(self, "return_dispatch", None);
        let target = self.words.len();
        // Caller values were spilled when it called; its assignment has not
        // been loaded yet. Do not spill this callee's stale physical pairs.
        self.mov(0, 31);
        self.return_to_vm();
        for at in vm {
            self.patch_conditional(at, target)?;
        }
        protocol_mark!(self, "return_dispatch_fallback", None);
        Ok(())
    }
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
#[path = "resumable_tests.rs"]
mod tests;
