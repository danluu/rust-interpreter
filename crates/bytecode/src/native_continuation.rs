//! Checked publication of a resumable native entry's guest state.
//!
//! Native execution can push and pop guest frames without returning to the VM.
//! A continuation therefore names the resulting top frame, not necessarily the
//! function that entered native code. This module validates host extents before
//! publishing any of them. It does not implement guest Calls or their effects.
use crate::{Frame, Frames, Limits, Memory, Program};

/// Initialized backing bounds, frozen for one native entry. Preparation does
/// not itself publish these bounds as live guest memory, registers or frames.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Capacity {
    pub memory: usize,
    pub registers: usize,
    pub frames: usize,
}

/// Mutable host cursor prefix for the future resumable emitter. The first two
/// fields match the ordinary JIT cursor's remaining-budget and profile pointer.
/// A containing cursor will add immutable backing pointers and entry tables.
#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub(crate) struct State {
    pub remaining: u64,
    pub profile_hits: *mut u64,
    pub memory_len: usize,
    pub peak_linear: usize,
    pub register_len: usize,
    pub frame_len: usize,
    /// Successfully pushed/popped guest frames; a faulting copy is not a push.
    pub calls: u64,
    pub returns: u64,
}

pub(crate) mod layout {
    use super::State;
    pub const REMAINING: usize = std::mem::offset_of!(State, remaining);
    pub const PROFILE_HITS: usize = std::mem::offset_of!(State, profile_hits);
    pub const MEMORY_LEN: usize = std::mem::offset_of!(State, memory_len);
    pub const PEAK_LINEAR: usize = std::mem::offset_of!(State, peak_linear);
    pub const REGISTER_LEN: usize = std::mem::offset_of!(State, register_len);
    pub const FRAME_LEN: usize = std::mem::offset_of!(State, frame_len);
    pub const CALLS: usize = std::mem::offset_of!(State, calls);
    pub const RETURNS: usize = std::mem::offset_of!(State, returns);

    #[cfg(all(target_arch = "aarch64", target_os = "macos"))]
    const _: () = {
        assert!(REMAINING == 0 && PROFILE_HITS == 8 && MEMORY_LEN == 16 && PEAK_LINEAR == 24);
        assert!(REGISTER_LEN == 32 && FRAME_LEN == 40 && CALLS == 48 && RETURNS == 56);
        assert!(std::mem::size_of::<State>() == 64 && std::mem::align_of::<State>() == 8);
    };
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Position {
    pub depth: usize,
    pub function: usize,
    pub pc: usize,
}

/// The JIT decodes its native status into this before validating publication.
/// Fault identities remain host-owned; they never name guest strings/pointers.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Status {
    Continue,
    Fault(u64),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Exit {
    /// No instruction consumed and no visible cursor/top-frame change. The VM
    /// must interpret the declined operation once before trying native again.
    Declined,
    /// Some instructions consumed, possibly ending in an ancestor/descendant.
    Resume(Position),
    /// Terminal guest failure. Extents are valid, but no later guest operation
    /// or result copy may execute. The JIT resolves the host-owned fault code.
    Fault(u64),
}

#[derive(Debug)]
pub(crate) struct Run {
    pub exit: Exit,
    pub instructions: u64,
    pub calls: u64,
    pub returns: u64,
}

pub(crate) struct Boundary {
    initial: State,
    entry: Frame,
    capacity: Capacity,
    fixed_bytes: usize,
    memory_limit: usize,
    frame_limit: usize,
    readonly_end: usize,
    memory_pointer: *const u8,
    heap_pointer: *const u8,
    registers_pointer: *const u128,
    frames_pointer: *const Frame,
}

impl Boundary {
    /// Capture one prepared VM state for a validated Program. No frame or slice
    /// from this call is retained while native code executes.
    pub fn new(
        program: &Program,
        memory: &Memory,
        registers: &[u128],
        frames: &Frames,
        register_bytes: usize,
        budget: u64,
        limits: &Limits,
        capacity: Capacity,
        profile_hits: *mut u64,
    ) -> Result<Self, String> {
        if register_bytes % 16 != 0
            || capacity.memory > memory.bytes.initialized_len()
            || capacity.registers > registers.len()
            || capacity.frames > frames.initialized_len()
        {
            return Err("invalid prepared native backing".into());
        }
        let initial = State {
            remaining: budget,
            profile_hits,
            memory_len: memory.bytes.len(),
            peak_linear: memory.bytes.len(),
            register_len: register_bytes / 16,
            frame_len: frames.len(),
            calls: 0,
            returns: 0,
        };
        let entry = *frames.last().ok_or("missing native entry frame")?;
        let boundary = Self {
            initial,
            entry,
            capacity,
            fixed_bytes: memory
                .heap
                .bytes
                .len()
                .checked_add(memory.auxiliary_bytes)
                .ok_or("native fixed memory size overflow")?,
            memory_limit: limits.memory,
            frame_limit: limits.frames,
            readonly_end: memory.readonly_end,
            memory_pointer: memory.bytes.as_ptr(),
            heap_pointer: memory.heap.bytes.as_ptr(),
            registers_pointer: registers.as_ptr(),
            frames_pointer: frames.as_ptr(),
        };
        boundary.validate_extents(program, frames, initial)?;
        Ok(boundary)
    }

    pub fn state(&self) -> State {
        self.initial
    }

    fn validate_extents(
        &self,
        program: &Program,
        frames: &Frames,
        state: State,
    ) -> Result<Frame, String> {
        if state.frame_len == 0
            || state.frame_len > self.capacity.frames
            || state.frame_len > self.frame_limit
            || state.register_len > self.capacity.registers
            || state.memory_len > state.peak_linear
            || state.peak_linear < self.initial.memory_len
            || state.peak_linear > self.capacity.memory
        {
            return Err("native continuation returned an invalid storage extent".into());
        }
        let working = state
            .register_len
            .checked_mul(16)
            .and_then(|n| n.checked_add(state.memory_len))
            .and_then(|n| n.checked_add(self.fixed_bytes));
        let peak = state.peak_linear.checked_add(self.fixed_bytes);
        if working.is_none_or(|n| n > self.memory_limit)
            || peak.is_none_or(|n| n > self.memory_limit)
        {
            return Err("native continuation exceeded a guest memory budget".into());
        }
        let frame = *frames
            .prepared_frame(state.frame_len - 1)
            .ok_or("native continuation has no prepared frame")?;
        let function = program
            .functions
            .get(frame.function)
            .ok_or("native continuation returned an invalid function")?;
        // Permit one-past-code, matching ordinary JIT fallback. The VM checks
        // exhaustion before diagnosing a missing bytecode terminator.
        if frame.pc > function.code.len()
            || frame.base == 0
            || frame.base < self.readonly_end
            || frame.base % function.frame_align != 0
            || frame
                .base
                .checked_add(function.frame_size.max(1))
                .is_none_or(|end| end > state.memory_len)
            || frame.register_base.checked_add(function.registers) != Some(state.register_len)
        {
            return Err("native continuation returned an invalid top frame".into());
        }
        if frame.return_value {
            let caller = state.frame_len.checked_sub(2).and_then(|i| frames.prepared_frame(i))
                .ok_or("native value return has no caller")?;
            let caller_function = program.functions.get(caller.function).ok_or("native value return has invalid caller")?;
            if program.version != crate::scalar_abi::SCALAR_VERSION || frame.tls_callback
                || !crate::scalar_calls::scalar_width(function.result.size)
                || frame.return_address >= caller_function.registers
                || caller.register_base.checked_add(caller_function.registers) != Some(frame.register_base) {
                return Err("native continuation returned an invalid value destination".into());
            }
        }
        Ok(frame)
    }

    /// Validate all publication fields before changing active host extents.
    /// The emitter separately maintains every ancestor descriptor, required
    /// zeroing/copy order and limits at each intermediate native Call. Checking
    /// the final top frame cannot prove that an earlier transient fit a budget.
    ///
    /// Fault exits are terminal. A fault during Call setup can advance the
    /// live memory end before pushing a frame, and descriptors need not carry
    /// a resumable fault PC. Validation here does not make that partial state
    /// resumable; a future recoverable-fault API needs its own rollback or
    /// committed-state contract.
    pub fn finish(
        self,
        program: &Program,
        memory: &mut Memory,
        registers: &[u128],
        frames: &mut Frames,
        register_bytes: &mut usize,
        state: State,
        status: Status,
    ) -> Result<Run, String> {
        // The backing and fixed accounting must still cover the exact entry
        // contract. Native code may not move storage or allocate TLS/heap data.
        if self.capacity.memory > memory.bytes.initialized_len()
            || self.capacity.registers > registers.len()
            || self.capacity.frames > frames.initialized_len()
            || memory.heap.bytes.len().checked_add(memory.auxiliary_bytes) != Some(self.fixed_bytes)
            || memory.readonly_end != self.readonly_end
            || memory.bytes.as_ptr() != self.memory_pointer
            || memory.heap.bytes.as_ptr() != self.heap_pointer
            || registers.as_ptr() != self.registers_pointer
            || frames.as_ptr() != self.frames_pointer
            || memory.bytes.len() != self.initial.memory_len
            || frames.len() != self.initial.frame_len
            || *register_bytes != self.initial.register_len * 16
        {
            return Err("native continuation backing changed during execution".into());
        }
        let instructions = self
            .initial
            .remaining
            .checked_sub(state.remaining)
            .ok_or("native continuation increased its budget")?;
        let transitions = state.calls.checked_add(state.returns);
        let depth = (self.initial.frame_len as u64)
            .checked_add(state.calls)
            .and_then(|n| n.checked_sub(state.returns));
        if transitions.is_none_or(|n| n > instructions) || depth != Some(state.frame_len as u64) {
            return Err("native continuation returned invalid call accounting".into());
        }
        let frame = self.validate_extents(program, frames, state)?;
        let exit = if instructions == 0 {
            if status != Status::Continue
                || frame != self.entry
                || state.memory_len != self.initial.memory_len
                || state.register_len != self.initial.register_len
                || state.frame_len != self.initial.frame_len
                || state.peak_linear != self.initial.peak_linear
                || state.profile_hits != self.initial.profile_hits
            {
                return Err("native continuation changed state without progress".into());
            }
            Exit::Declined
        } else {
            match status {
                Status::Continue => Exit::Resume(Position {
                    depth: state.frame_len,
                    function: frame.function,
                    pc: frame.pc,
                }),
                Status::Fault(code) => Exit::Fault(code),
            }
        };
        // All arithmetic and all three bounds have already passed. No fallible
        // guest operation, allocation or user code runs between these commits.
        memory.bytes.commit_native_len(state.memory_len)?;
        frames.commit_native_len(state.frame_len)?;
        *register_bytes = state.register_len * 16;
        memory.peak = memory.peak.max(state.peak_linear + self.fixed_bytes);
        Ok(Run {
            exit,
            instructions,
            calls: state.calls,
            returns: state.returns,
        })
    }
}

#[cfg(test)]
mod tests;
