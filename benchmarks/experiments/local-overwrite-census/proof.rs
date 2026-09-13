//! Diagnostic only: a write is dead only after every byte is overwritten.
use crate::{Binary, Function, Op, Reg};
use serde::Serialize;

pub const MAX_FRAME: usize = 8192;
pub const MAX_REGISTERS: usize = 16384;
pub const MAX_REGION: usize = 1024;
pub const MAX_WORK: usize = 4_000_000;
pub const MAX_GLOBAL_WORK: usize = 256_000_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Fact { Local(usize), Constant(u128) }

#[derive(Debug, Serialize)]
pub struct Candidate {
    pub pc: usize,
    pub operation: &'static str,
    pub offset: usize,
    pub size: usize,
    pub overwritten_at: usize,
}

struct Pending { candidate: Candidate, remaining: usize, observed: bool }

#[derive(Debug, Serialize)]
pub struct Report {
    pub candidates: Vec<Candidate>,
    pub writes: usize,
    pub barriers: usize,
    pub work: usize,
    pub decline: Option<&'static str>,
}

struct State {
    facts: Vec<Option<Fact>>,
    owners: Vec<Option<usize>>,
    writes: Vec<Pending>,
    barriers: usize,
    work: usize,
    limit: usize,
}

impl State {
    fn charge(&mut self, n: usize) -> Option<()> {
        self.work = self.work.checked_add(n)?;
        (self.work <= self.limit).then_some(())
    }
    fn range(&self, r: Reg, size: usize) -> Option<std::ops::Range<usize>> {
        let Some(Fact::Local(offset)) = self.facts[r as usize] else { return None; };
        let end = offset.checked_add(size)?;
        (end <= self.owners.len()).then_some(offset..end)
    }
    fn length(&self, r: Reg) -> Option<usize> {
        let Some(Fact::Constant(value)) = self.facts[r as usize] else { return None; };
        usize::try_from(value).ok()
    }
    fn barrier(&mut self) -> Option<()> {
        self.charge(self.writes.len() + self.owners.len() + 1)?;
        self.barriers += 1;
        for w in &mut self.writes { if w.remaining != 0 { w.observed = true; } }
        self.owners.fill(None);
        Some(())
    }
    fn read(&mut self, range: std::ops::Range<usize>) -> Option<()> {
        self.charge(range.len())?;
        for offset in range {
            if let Some(owner) = self.owners[offset] { self.writes[owner].observed = true; }
        }
        Some(())
    }
    fn write(&mut self, range: std::ops::Range<usize>, pc: usize, operation: &'static str) -> Option<()> {
        self.charge(range.len() + 1)?;
        if range.is_empty() { return Some(()); }
        let index = self.writes.len();
        let candidate = Candidate { pc, operation, offset:range.start, size:range.len(), overwritten_at:pc };
        self.writes.push(Pending { remaining:range.len(), candidate, observed:false });
        for offset in range {
            if let Some(owner) = self.owners[offset] {
                let previous = &mut self.writes[owner];
                // Each owned byte is removed once, even after an observation.
                previous.remaining -= 1;
                if previous.remaining == 0 { previous.candidate.overwritten_at = pc; }
            }
            self.owners[offset] = Some(index);
        }
        Some(())
    }
    fn step(&mut self, pc: usize, op: &Op) -> Option<()> {
        // Facts and memory operands are captured before aliased outputs die.
        let mut outputs = vec![];
        match *op {
            Op::Local {dst,offset} => outputs.push((dst,Fact::Local(offset))),
            Op::Imm {dst,value} => outputs.push((dst,Fact::Constant(value))),
            Op::Binary {dst,overflow,op:Binary::Add,a,b,bits:64,signed:false} => {
                let pair = match (self.facts[a as usize],self.facts[b as usize]) {
                    (Some(Fact::Local(offset)),Some(Fact::Constant(add)))
                    | (Some(Fact::Constant(add)),Some(Fact::Local(offset))) => Some((offset,add)),
                    _ => None,
                };
                if let Some((offset,add)) = pair {
                    if let Some(end) = offset.checked_add(add as u64 as usize).filter(|&end|end <= self.owners.len()) {
                        outputs.push((dst,Fact::Local(end)));
                        outputs.push((overflow,Fact::Constant(0)));
                    }
                }
            }
            _ => {},
        }
        match *op {
            Op::Load {address,size,..} => {
                if let Some(range) = self.range(address,size as usize) { self.read(range)?; }
                else { self.barrier()?; }
            }
            Op::Store {address,size,..} => {
                if let Some(range) = self.range(address,size as usize) { self.write(range,pc,"Store")?; }
                else { self.barrier()?; }
            }
            Op::Copy {dst,src,size} => {
                if let (Some(source),Some(destination)) = (self.range(src,size),self.range(dst,size)) {
                    self.read(source)?; self.write(destination,pc,"Copy")?;
                } else { self.barrier()?; }
            }
            Op::FillBytes {address,size,..} => {
                if let Some(range) = self.length(size).and_then(|n|self.range(address,n)) { self.write(range,pc,"FillBytes")?; }
                else { self.barrier()?; }
            }
            Op::Binary {op:Binary::Div|Binary::Rem,..} => self.barrier()?,
            Op::Imm {..}|Op::Local {..}|Op::Binary {..}|Op::Unary {..}|Op::Cast {..}|Op::Select {..} => {},
            // Including control transfers, assertions, unknown memory effects,
            // floating operations and all unsupported transfers. No proof of
            // later bytes can cross a possible error or observable exit.
            _ => self.barrier()?,
        }
        let mut operands = 1;
        crate::registers::visit_registers(op, |_|operands+=1, |r|self.facts[r as usize]=None);
        self.charge(operands + outputs.len())?;
        // Match interpreter ordering: overflow overwrites an aliased result.
        for (r,fact) in outputs { self.facts[r as usize]=Some(fact); }
        Some(())
    }
}

pub fn analyze(f: &Function, start: usize, end: usize, remaining: &mut usize) -> Report {
    let decline = |reason,work| Report {candidates:vec![],writes:0,barriers:0,work,decline:Some(reason)};
    if f.frame_size > MAX_FRAME || f.registers > MAX_REGISTERS || start >= end
        || end > f.code.len() || end-start > MAX_REGION { return decline("shape_limit",0); }
    let limit = MAX_WORK.min(*remaining);
    let initial = f.frame_size.max(1) + f.registers;
    if initial > limit { *remaining = remaining.saturating_sub(limit); return decline("work_limit",limit); }
    let mut state = State {facts:vec![None;f.registers],owners:vec![None;f.frame_size.max(1)],
        writes:vec![],barriers:0,work:initial,limit};
    let completed = (start..end).try_for_each(|pc|state.step(pc,&f.code[pc])).and_then(|()|state.barrier());
    let used = state.work.min(limit); *remaining -= used;
    if completed.is_none() { return decline("work_limit",used); }
    let writes = state.writes.len();
    let candidates = state.writes.into_iter().filter(|w|w.remaining==0 && !w.observed).map(|w|w.candidate).collect();
    Report {candidates,writes,barriers:state.barriers,work:used,decline:None}
}

#[cfg(test)]
#[path="proof_tests.rs"]
mod tests;
