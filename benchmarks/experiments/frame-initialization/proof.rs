//! Diagnostic only: prove independence from a callee frame's initial bytes.
use crate::{Function, Op, Reg, Slot};
use serde::Serialize;

const MAX_FRAME: usize = 8192;
const MAX_OPS: usize = 4096;
const MAX_REGISTERS: usize = 16384;
const MAX_WORK: usize = 1_000_000;

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Decline {
    pub pc: usize,
    pub reason: &'static str,
}

#[derive(Debug, Serialize)]
pub struct Proof {
    pub eligible: bool,
    pub decline: Option<Decline>,
    pub work: usize,
}

struct State {
    bytes: Vec<bool>,
    initialized: usize,
    locals: Vec<Option<usize>>,
    work: usize,
    pc: usize,
}

impl State {
    fn fail(&self, reason: &'static str) -> Decline { Decline { pc: self.pc, reason } }

    fn charge(&mut self, amount: usize) -> Result<(), Decline> {
        self.work = self.work.saturating_add(amount);
        if self.work > MAX_WORK { Err(self.fail("work_limit")) } else { Ok(()) }
    }

    fn read(&mut self, offset: Option<usize>, size: usize) -> Result<(), Decline> {
        if size == 0 { return Ok(()); }
        let Some(offset) = offset else { return self.unknown("unknown_pointer_read"); };
        let Some(end) = offset.checked_add(size).filter(|&end| end <= self.bytes.len()) else {
            return Err(self.fail("read_outside_frame"));
        };
        self.charge(size)?;
        if self.bytes[offset..end].iter().all(|&b| b) { Ok(()) }
        else { Err(self.fail("local_read_before_write")) }
    }

    fn write(&mut self, offset: Option<usize>, size: usize) -> Result<(), Decline> {
        // Unknown destinations may alias the frame, but establish no facts.
        let Some(offset) = offset else { return Ok(()); };
        let Some(end) = offset.checked_add(size).filter(|&end| end <= self.bytes.len()) else {
            return Err(self.fail("write_outside_frame"));
        };
        self.charge(size)?;
        for b in &mut self.bytes[offset..end] {
            if !*b { *b = true; self.initialized += 1; }
        }
        Ok(())
    }

    fn unknown(&self, reason: &'static str) -> Result<(), Decline> {
        if self.initialized == self.bytes.len() { Ok(()) } else { Err(self.fail(reason)) }
    }

    fn reset(&mut self, args: &[Slot]) -> Result<(), Decline> {
        self.charge(self.bytes.len() + self.locals.len())?;
        self.bytes.fill(false);
        self.locals.fill(None);
        self.initialized = 0;
        for arg in args { self.write(Some(arg.offset), arg.size)?; }
        Ok(())
    }

    fn op(&mut self, op: &Op, result: Slot) -> Result<(), Decline> {
        self.charge(1)?;
        match op {
            Op::Load { address, size, .. } => self.read(self.locals[*address as usize], *size as usize)?,
            Op::Store { address, size, .. } => self.write(self.locals[*address as usize], *size as usize)?,
            Op::Copy { dst, src, size } => {
                // Overlap is allowed: a write cannot justify its own source.
                self.read(self.locals[*src as usize], *size)?;
                self.write(self.locals[*dst as usize], *size)?;
            }
            Op::Return => self.read(Some(result.offset), result.size)?,
            Op::Imm { .. } | Op::Local { .. } | Op::Binary { .. } | Op::Unary { .. }
            | Op::Cast { .. } | Op::Select { .. } | Op::Jump { .. } | Op::Switch { .. }
            | Op::Assert { .. } | Op::Trap { .. } | Op::FloatBinary { .. }
            | Op::FloatUnary { .. } | Op::FloatConvert { .. } => {}
            // These can inspect memory through aliases, dynamic sizes or a
            // nested call. Once every byte is written, initial clearing cannot
            // matter; before that point this proof makes no effect assumptions.
            Op::Call { .. } | Op::CallIndirect { .. } | Op::CopyDynamic { .. }
            | Op::CompareBytes { .. } | Op::Allocate { .. } | Op::Deallocate { .. }
            | Op::Reallocate { .. } | Op::FillBytes { .. } | Op::RandomBytes { .. }
            | Op::CpuFeatureQuery { .. } | Op::CAllocate { .. } | Op::CDeallocate { .. }
            | Op::CReallocate { .. } | Op::CAlignedAllocate { .. }
            | Op::RegisterTlsDestructor { .. } | Op::ResetThreadLocals => self.unknown("unknown_memory_effect")?,
        }
        // Read all memory operands before invalidating aliased outputs.
        crate::registers::visit_registers(op, |_| {}, |r: Reg| self.locals[r as usize] = None);
        if let Op::Local { dst, offset } = op { self.locals[*dst as usize] = Some(*offset); }
        Ok(())
    }
}

/// Input must have passed the ordinary Program validator. No transformed
/// program or runtime option is produced. Caller-local argument sources and
/// separately cleared alignment padding are additional call-site obligations.
pub fn analyze(function: &Function) -> Proof {
    if function.frame_size > MAX_FRAME || function.code.len() > MAX_OPS
        || function.registers > MAX_REGISTERS || function.args.len() > MAX_OPS
    {
        return Proof { eligible: false, decline: Some(Decline { pc: 0, reason: "size_limit" }), work: 0 };
    }
    let mut s = State { bytes: vec![false; function.frame_size.max(1)], initialized: 0,
        locals: vec![None; function.registers], work: 0, pc: 0 };
    let result = (|| {
        let mut starts = vec![false; function.code.len()];
        starts[0] = true;
        for (pc, op) in function.code.iter().enumerate() {
            s.pc = pc;
            s.charge(1)?;
            match op {
                Op::Jump { target } => starts[*target] = true,
                Op::Switch { cases, otherwise, .. } => {
                    s.charge(cases.len())?;
                    starts[*otherwise] = true;
                    for (_, target) in cases { starts[*target] = true; }
                }
                _ => {}
            }
            if matches!(op, Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. })
                && pc + 1 < starts.len() { starts[pc + 1] = true; }
        }
        for (pc, op) in function.code.iter().enumerate() {
            s.pc = pc;
            if starts[pc] { s.reset(&function.args)?; }
            s.op(op, function.result)?;
        }
        Ok(())
    })();
    Proof { eligible: result.is_ok(), decline: result.err(), work: s.work }
}

#[cfg(test)]
#[path = "proof_tests.rs"]
mod tests;
