//! Diagnostic only: definite initialization and confined direct-callee effects.
use crate::{Binary, Function, Op, Program};
use serde::Serialize;
use std::collections::VecDeque;

const MAX_FRAME: usize = 8192;
const MAX_OPS: usize = 4096;
const MAX_REGISTERS: usize = 16384;
const MAX_BLOCKS: usize = 512;
const MAX_EDGES: usize = 8192;
const MAX_STATE_BYTES: usize = 16 * 1024 * 1024;
const MAX_WORK: usize = 4_000_000;
pub const MAX_GLOBAL_WORK: usize = 256_000_000;
const MAX_FUNCTIONS: usize = 65536;
const MAX_PROGRAM_OPS: usize = 2_000_000;

#[derive(Clone, Debug, Serialize)]
pub struct Proof {
    pub eligible: bool,
    pub decline: Option<Decline>,
    pub work: usize,
}
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Decline { pub pc: usize, pub reason: &'static str }
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Mode { Confined, Initialized }
#[derive(Clone, PartialEq, Eq)]
struct State { bytes: Vec<bool>, facts: Vec<Option<Fact>> }
#[derive(Clone, Copy, PartialEq, Eq)]
enum Fact { Local(usize), Constant(u128) }
impl State {
    fn local(&self, reg: u32) -> Option<usize> {
        match self.facts[reg as usize] { Some(Fact::Local(offset)) => Some(offset), _ => None }
    }
    fn size(&self, reg: u32) -> Option<usize> {
        match self.facts[reg as usize] { Some(Fact::Constant(n)) => usize::try_from(n).ok(), _ => None }
    }
}
struct Block { start: usize, end: usize, successors: Vec<usize> }
struct Analysis<'a> {
    program: &'a Program, confined: &'a [bool], mode: Mode,
    work: usize, max_work: usize, pc: usize,
}

impl Analysis<'_> {
    fn fail(&self, reason: &'static str) -> Decline { Decline { pc: self.pc, reason } }
    fn charge(&mut self, amount: usize) -> Result<(), Decline> {
        self.work = self.work.saturating_add(amount);
        if self.work > self.max_work { Err(self.fail("work_limit")) } else { Ok(()) }
    }
    fn unknown(&mut self, state: &State, reason: &'static str) -> Result<(), Decline> {
        if self.mode == Mode::Initialized { self.charge(state.bytes.len())?; }
        if self.mode == Mode::Initialized && state.bytes.iter().all(|b| *b) { Ok(()) }
        else { Err(self.fail(reason)) }
    }
    fn range(&self, state: &State, offset: usize, size: usize) -> Result<std::ops::Range<usize>, Decline> {
        let end = offset.checked_add(size).filter(|end| *end <= state.bytes.len())
            .ok_or_else(|| self.fail("outside_frame"))?;
        Ok(offset..end)
    }
    fn read(&mut self, state: &State, offset: Option<usize>, size: usize) -> Result<(), Decline> {
        if size == 0 { return Ok(()); }
        self.charge(size)?;
        let Some(offset) = offset else { return self.unknown(state, "unknown_pointer_read"); };
        let range = self.range(state, offset, size)?;
        if self.mode == Mode::Confined || state.bytes[range].iter().all(|b| *b) { Ok(()) }
        else { Err(self.fail("local_read_before_write")) }
    }
    fn write(&mut self, state: &mut State, offset: Option<usize>, size: usize) -> Result<(), Decline> {
        if size == 0 { return Ok(()); }
        self.charge(size)?;
        let Some(offset) = offset else {
            return if self.mode == Mode::Confined { Err(self.fail("unknown_pointer_write")) } else { Ok(()) };
        };
        let range = self.range(state, offset, size)?;
        if self.mode == Mode::Initialized { state.bytes[range].fill(true); }
        Ok(())
    }
    fn transfer(&mut self, state: &mut State, op: &Op, f: &Function) -> Result<(), Decline> {
        self.charge(1)?;
        match op {
            Op::Load { address, size, .. } => self.read(state, state.local(*address), *size as usize)?,
            Op::Store { address, size, .. } => {
                let offset = state.local(*address); self.write(state, offset, *size as usize)?;
            }
            Op::Copy { dst, src, size } => {
                self.read(state, state.local(*src), *size)?;
                let offset = state.local(*dst); self.write(state, offset, *size)?;
            }
            Op::FillBytes { address, size, .. } if state.size(*size).is_some() => {
                let (offset, size) = (state.local(*address), state.size(*size).unwrap());
                self.write(state, offset, size)?;
            }
            Op::CopyDynamic { dst, src, size } if state.size(*size).is_some() => {
                let size = state.size(*size).unwrap();
                self.read(state, state.local(*src), size)?;
                let offset = state.local(*dst); self.write(state, offset, size)?;
            }
            Op::CompareBytes { left, right, size, .. } if state.size(*size).is_some() => {
                let size = state.size(*size).unwrap();
                self.read(state, state.local(*left), size)?;
                self.read(state, state.local(*right), size)?;
            }
            Op::Call { function, args, destination } if self.confined[*function] => {
                let program = self.program; let callee = &program.functions[*function];
                self.charge(args.len())?;
                // All argument reads precede the callee's returned result write.
                for (&reg, slot) in args.iter().zip(&callee.args) {
                    self.read(state, state.local(reg), slot.size)?;
                }
                let offset = state.local(*destination); self.write(state, offset, callee.result.size)?;
            }
            Op::Return => self.read(state, Some(f.result.offset), f.result.size)?,
            Op::Imm { .. } | Op::Local { .. } | Op::Binary { .. } | Op::Unary { .. }
            | Op::Cast { .. } | Op::Select { .. } | Op::Jump { .. } | Op::Switch { .. }
            | Op::Assert { .. } | Op::Trap { .. } | Op::FloatBinary { .. }
            | Op::FloatUnary { .. } | Op::FloatConvert { .. } => {}
            _ => self.unknown(state, "unknown_memory_effect")?,
        }
        // Compute facts from the old inputs, then apply outputs in VM order.
        let mut outputs = vec![];
        match *op {
            Op::Local {dst,offset} => outputs.push((dst,Fact::Local(offset))),
            Op::Imm {dst,value} => outputs.push((dst,Fact::Constant(value))),
            Op::Binary {dst,overflow,op:Binary::Add,a,b,bits:64,signed:false} => {
                let pair = match (state.facts[a as usize],state.facts[b as usize]) {
                    (Some(Fact::Local(offset)),Some(Fact::Constant(add))) |
                    (Some(Fact::Constant(add)),Some(Fact::Local(offset))) => Some((offset,add)),
                    _ => None,
                };
                if let Some((offset,add))=pair {
                    if let Some(end)=offset.checked_add(add as u64 as usize).filter(|end| *end<=f.frame_size.max(1)) {
                        outputs.push((dst,Fact::Local(end)));outputs.push((overflow,Fact::Constant(0)));
                    }
                }
            }
            _ => {},
        }
        crate::registers::visit_registers(op, |_| {}, |reg| state.facts[reg as usize] = None);
        for (reg,fact) in outputs { state.facts[reg as usize] = Some(fact); }
        Ok(())
    }
    fn blocks(&mut self, f: &Function) -> Result<Vec<Block>, Decline> {
        let mut starts = vec![false; f.code.len()]; starts[0] = true;
        let mut edges = 0usize;
        for (pc, op) in f.code.iter().enumerate() {
            self.pc = pc; self.charge(1)?;
            match op {
                Op::Jump { target } => { starts[*target] = true; edges += 1; }
                Op::Switch { cases, otherwise, .. } => {
                    edges = edges.saturating_add(cases.len()).saturating_add(1);
                    if edges > MAX_EDGES { return Err(self.fail("edge_limit")); }
                    starts[*otherwise] = true;
                    for (_, target) in cases { starts[*target] = true; }
                    self.charge(cases.len())?;
                }
                _ => {}
            }
            if matches!(op, Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }) && pc+1 < starts.len() {
                starts[pc+1] = true;
            }
        }
        let indices: Vec<_> = starts.iter().enumerate().filter_map(|(i, &yes)| yes.then_some(i)).collect();
        if indices.len() > MAX_BLOCKS { return Err(self.fail("block_limit")); }
        let state_bytes = f.frame_size.max(1).checked_add(f.registers.checked_mul(std::mem::size_of::<Option<Fact>>())
            .ok_or_else(|| self.fail("state_limit"))?).ok_or_else(|| self.fail("state_limit"))?;
        if state_bytes.checked_mul(indices.len()+2).is_none_or(|n| n > MAX_STATE_BYTES) {
            return Err(self.fail("state_limit"));
        }
        let mut owner = vec![0; f.code.len()];
        for (index, &start) in indices.iter().enumerate() {
            owner[start..indices.get(index+1).copied().unwrap_or(f.code.len())].fill(index);
        }
        let mut blocks = vec![];
        for (index, &start) in indices.iter().enumerate() {
            let end = indices.get(index+1).copied().unwrap_or(f.code.len());
            let mut successors = match &f.code[end-1] {
                Op::Jump { target } => vec![owner[*target]],
                Op::Switch { cases, otherwise, .. } => cases.iter().map(|(_, target)| owner[*target])
                    .chain(std::iter::once(owner[*otherwise])).collect(),
                Op::Return | Op::Trap { .. } => vec![],
                _ if end < f.code.len() => vec![owner[end]],
                _ => vec![], // one-past-code is terminal failure, not a return
            };
            successors.sort_unstable(); successors.dedup();
            blocks.push(Block { start, end, successors });
        }
        Ok(blocks)
    }
    fn solve(&mut self, f: &Function) -> Result<(Vec<Block>, Vec<Option<State>>), Decline> {
        let blocks = self.blocks(f)?;
        let mut initial = State { bytes: vec![false; f.frame_size.max(1)], facts: vec![None; f.registers] };
        if self.mode == Mode::Initialized {
            for slot in &f.args { self.write(&mut initial, Some(slot.offset), slot.size)?; }
        }
        let state_work = f.frame_size.max(1) + f.registers;
        let mut states = vec![None; blocks.len()]; states[0] = Some(initial);
        let mut pending = VecDeque::from([0]); let mut queued = vec![false; blocks.len()]; queued[0] = true;
        while let Some(index) = pending.pop_front() {
            queued[index] = false; self.pc = blocks[index].start; self.charge(state_work)?;
            let mut state = states[index].as_ref().unwrap().clone();
            for pc in blocks[index].start..blocks[index].end {
                self.pc = pc; self.transfer(&mut state, &f.code[pc], f)?;
            }
            for &next in &blocks[index].successors {
                self.charge(state_work)?;
                let changed = match &mut states[next] {
                    None => { states[next] = Some(state.clone()); true }
                    Some(previous) => {
                        let mut changed = false;
                        for (a, b) in previous.bytes.iter_mut().zip(&state.bytes) {
                            if *a && !*b { *a = false; changed = true; }
                        }
                        for (a, b) in previous.facts.iter_mut().zip(&state.facts) {
                            if a.is_some() && a != b { *a = None; changed = true; }
                        }
                        changed
                    }
                };
                if changed && !queued[next] { queued[next] = true; pending.push_back(next); }
            }
        }
        Ok((blocks, states))
    }
    fn run(&mut self, f: &Function) -> Result<(), Decline> {
        self.solve(f).map(|_| ())
    }
}

/// Validated input only. This proof applies to ordinary execution from PC zero.
pub fn analyze(program: &Program, id: usize, confined: &[bool], mode: Mode) -> Proof {
    analyze_with_work(program, id, confined, mode, MAX_WORK)
}
pub fn analyze_budgeted(program: &Program, id: usize, confined: &[bool], mode: Mode, remaining: &mut usize) -> Proof {
    if *remaining == 0 { return Proof { eligible:false, decline:Some(Decline {pc:0,reason:"global_work_limit"}),work:0 }; }
    let proof = analyze_with_work(program, id, confined, mode, MAX_WORK.min(*remaining));
    *remaining = remaining.saturating_sub(proof.work);
    proof
}
fn analyze_with_work(program: &Program, id: usize, confined: &[bool], mode: Mode, max_work: usize) -> Proof {
    let f = &program.functions[id]; assert_eq!(confined.len(), program.functions.len());
    if f.code.is_empty() || f.code.len() > MAX_OPS || f.frame_size > MAX_FRAME || f.registers > MAX_REGISTERS {
        return Proof { eligible: false, decline: Some(Decline { pc: 0, reason: "size_limit" }), work: 0 };
    }
    let mut a = Analysis { program, confined, mode, work: 0, max_work, pc: 0 };
    let result = a.run(f);
    Proof { eligible: result.is_ok(), decline: result.err(), work: a.work }
}

pub fn effects(program: &Program) -> Vec<Proof> {
    let n = program.functions.len();
    assert!(n <= MAX_FUNCTIONS && program.functions.iter().map(|f| f.code.len()).sum::<usize>() <= MAX_PROGRAM_OPS,
        "program exceeds diagnostic admission bounds");
    let mut remaining = MAX_GLOBAL_WORK;
    let mut color = vec![0u8; n]; let mut confined = vec![false; n]; let mut proofs = vec![None; n];
    for root in 0..n {
        let mut pending = vec![(root, false)];
        while let Some((id, finish)) = pending.pop() {
            if color[id] == 2 { continue; }
            if finish {
                let result = analyze_budgeted(program, id, &confined, Mode::Confined, &mut remaining);
                confined[id] = result.eligible; proofs[id] = Some(result); color[id] = 2;
            } else if color[id] == 0 {
                color[id] = 1; pending.push((id, true));
                if program.functions[id].code.len() <= MAX_OPS {
                    for op in &program.functions[id].code {
                        if let Op::Call { function, .. } = op {
                            if color[*function] == 0 { pending.push((*function, false)); }
                        }
                    }
                }
            } // A visiting dependency remains unproved; no recursion assumption.
        }
    }
    proofs.into_iter().map(Option::unwrap).collect()
}

#[cfg(test)]
#[path = "proof_tests.rs"]
mod tests;

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod chain_census;

#[derive(Clone, Copy, Debug, Serialize, PartialEq, Eq)]
pub struct Access { pub offset: Option<usize>, pub size: usize }
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Resolved {
    pub pc: usize,
    pub reads: Vec<Access>,
    pub writes: Vec<Access>,
    pub terminal_or_assertion: bool,
}
#[derive(Debug, Serialize)]
pub struct MemoryPlan {
    pub eligible: bool,
    pub decline: Option<Decline>,
    pub work: usize,
    pub accesses: Vec<Resolved>,
}

/// Only a diagnostic annotation of ordinary entry from PC zero. No memory or
/// register is replaced, and this is not an address-nonescape certificate.
pub fn memory_plan(program: &Program, id: usize, remaining: &mut usize) -> MemoryPlan {
    let f=&program.functions[id];
    let declined=|reason| MemoryPlan {eligible:false,decline:Some(Decline{pc:0,reason}),work:0,accesses:vec![]};
    if f.code.is_empty() || f.code.len()>512 || f.frame_size>512 || f.registers>512 {
        return declined("small_shape_limit");
    }
    if f.code.iter().any(|op| matches!(op,Op::Call{..}|Op::CallIndirect{..})) {
        return declined("has_callee");
    }
    if f.args.iter().chain([&f.result]).any(|slot| !matches!(slot.size,0|1|2|4|8|16)) {
        return declined("boundary_width");
    }
    let confined=vec![false;program.functions.len()];
    let init=analyze_budgeted(program,id,&confined,Mode::Initialized,remaining);
    if !init.eligible { return MemoryPlan{eligible:false,decline:init.decline,work:init.work,accesses:vec![]}; }
    let mut a=Analysis {program,confined:&confined,mode:Mode::Confined,work:0,max_work:MAX_WORK.min(*remaining),pc:0};
    let mut accesses=vec![];
    let result=(|| {
        let (blocks,states)=a.solve(f)?;
        // A separate traversal reads the converged states. Provisional facts
        // seen during solving never become published access annotations.
        for (block,state) in blocks.iter().zip(states) {
            let Some(mut state)=state else { continue; };
            a.charge(f.frame_size.max(1)+f.registers)?;
            for pc in block.start..block.end {
                a.pc=pc;
                let op=&f.code[pc];
                let range=|offset:Option<usize>,size:usize| -> Result<Access,Decline> {
                    if size==0 { return Ok(Access{offset:None,size:0}); }
                    let offset=offset.ok_or(Decline{pc,reason:"unresolved_access"})?;
                    if offset.checked_add(size).is_none_or(|end|end>f.frame_size.max(1)) {
                        return Err(Decline{pc,reason:"outside_frame"});
                    }
                    Ok(Access{offset:Some(offset),size})
                };
                let mut row=Resolved{pc,reads:vec![],writes:vec![],terminal_or_assertion:matches!(op,Op::Assert{..}|Op::Trap{..}|Op::Return)};
                match op {
                    Op::Load{address,size,..} => row.reads.push(range(state.local(*address),*size as usize)?),
                    Op::Store{address,size,..} => row.writes.push(range(state.local(*address),*size as usize)?),
                    Op::Copy{src,dst,size} => {
                        row.reads.push(range(state.local(*src),*size)?);
                        row.writes.push(range(state.local(*dst),*size)?);
                    }
                    Op::FillBytes{address,size,..} => {
                        let size=state.size(*size).ok_or(Decline{pc,reason:"unresolved_extent"})?;
                        row.writes.push(range(state.local(*address),size)?);
                    }
                    Op::CopyDynamic{src,dst,size} => {
                        let size=state.size(*size).ok_or(Decline{pc,reason:"unresolved_extent"})?;
                        row.reads.push(range(state.local(*src),size)?);row.writes.push(range(state.local(*dst),size)?);
                    }
                    Op::CompareBytes{left,right,size,..} => {
                        let size=state.size(*size).ok_or(Decline{pc,reason:"unresolved_extent"})?;
                        row.reads.push(range(state.local(*left),size)?);row.reads.push(range(state.local(*right),size)?);
                    }
                    Op::Return => row.reads.push(range(Some(f.result.offset),f.result.size)?),
                    _ => {},
                }
                a.transfer(&mut state,op,f)?;
                if !row.reads.is_empty() || !row.writes.is_empty() || row.terminal_or_assertion { accesses.push(row); }
            }
        }
        Ok(())
    })();
    *remaining=remaining.saturating_sub(a.work);
    match result {
        Ok(()) => MemoryPlan{eligible:true,decline:None,work:init.work+a.work,accesses},
        Err(decline) => MemoryPlan{eligible:false,decline:Some(decline),work:init.work+a.work,accesses:vec![]},
    }
}
