//! One guest thread's callbacks. Handles and data never enter the host TLS ABI.
use super::{Frame, Frames, Limits, Memory, Program, FUNCTION_POINTER_TAG};

struct Callback { function: usize, argument: usize }

pub(super) enum Completion { Entry(u128), Reset }

#[derive(Default)]
pub(super) struct Tls {
    callbacks: Vec<Callback>,
    pub completion: Option<Completion>,
}

impl Tls {
    pub fn is_empty(&self) -> bool { self.callbacks.is_empty() }

    pub fn register(&mut self, program: &Program, memory: &mut Memory,
        registers: usize, handle: u128, argument: u128) -> Result<(), String> {
        // Darwin does not support new _tlv_atexit registrations during teardown.
        // Rust's destructor-list reentrancy runs inside its already registered
        // callback and does not enter this foreign registration path again.
        if self.completion.is_some() { return Err("guest TLS registration during teardown".into()); }
        if handle > u64::MAX as u128 || handle as u64 & FUNCTION_POINTER_TAG == 0 {
            return Err("invalid guest TLS function pointer".into());
        }
        let id = ((handle as u64 & !FUNCTION_POINTER_TAG) as usize).checked_sub(1)
            .ok_or("null guest TLS function handle")?;
        let function = program.functions.get(id).ok_or("invalid guest TLS function handle")?;
        if function.args.len() != 1 || function.args[0].size != 8 || function.result.size != 0 {
            return Err("guest TLS callback signature mismatch".into());
        }
        let argument = usize::try_from(argument).map_err(|_| "guest TLS argument exceeds pointer width")?;
        let added = std::mem::size_of::<Callback>();
        if memory.total_len().checked_add(registers).and_then(|n| n.checked_add(added))
            .is_none_or(|n| n > memory.limit) {
            return Err("interpreter working-memory limit exceeded".into());
        }
        self.callbacks.push(Callback { function: id, argument });
        memory.auxiliary_bytes += added;
        memory.peak = memory.peak.max(memory.total_len());
        Ok(())
    }

    /// Start the next callback, or finish teardown. Called only at lifecycle
    /// transitions, without replaying a consumed Return or Reset instruction.
    pub fn advance(&mut self, program: &Program, memory: &mut Memory,
        frames: &mut Frames, registers: &mut Vec<u128>, register_bytes: &mut usize,
        needs_zeroes: &[bool], limits: &Limits) -> Result<Option<u128>, String> {
        if let Some(callback) = self.callbacks.pop() {
            memory.auxiliary_bytes -= std::mem::size_of::<Callback>();
            if frames.len() >= limits.frames {
                return Err("interpreter call-depth limit exceeded".into());
            }
            let function = &program.functions[callback.function];
            let base = memory.reserve_frame(function.frame_size, function.frame_align)?;
            let register_base = *register_bytes / 16;
            *register_bytes = function.registers.checked_mul(16)
                .and_then(|n| n.checked_add(*register_bytes)).ok_or("register size overflow")?;
            if register_bytes.checked_add(memory.total_len()).is_none_or(|n| n > limits.memory) {
                return Err("interpreter working-memory limit exceeded".into());
            }
            let end = *register_bytes / 16;
            if end > registers.len() { registers.resize(end, 0); }
            if needs_zeroes[callback.function] { registers[register_base..end].fill(0); }
            memory.store(base + function.args[0].offset, 8, callback.argument as u128)?;
            frames.push(Frame { function: callback.function, pc: 0, base, register_base,
                return_address: 0, tls_callback: true, return_code_offset: 0 });
            return Ok(None);
        }
        match self.completion.take().ok_or("missing guest TLS completion")? {
            Completion::Entry(value) => Ok(Some(value)),
            Completion::Reset => {
                for slot in &program.thread_locals {
                    let range = slot.offset..slot.offset + slot.size;
                    memory.heap.bytes[range.clone()].copy_from_slice(&program.statics[range]);
                }
                Ok(None)
            }
        }
    }
}
