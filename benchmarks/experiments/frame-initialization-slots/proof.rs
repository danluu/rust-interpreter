//! Diagnostic only: definite initialization and confined direct-callee effects.
use crate::{Binary, Function, Op, Program};
use serde::Serialize;
use std::collections::{BTreeMap, VecDeque};

const MAX_SLOTS: usize = 64;
const MAX_COPY_FACT_BYTES: usize = 128;

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
struct State { bytes: Vec<bool>, facts: Vec<Option<Fact>>, slots: BTreeMap<usize, Fact> }
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
// Only complete eight-byte cells survive an exact bounded local memmove.
// Source facts are read before destination invalidation, including overlap.
fn copied_slots(state: &State, dst: u32, src: u32, size: usize) -> Vec<(usize,Fact)> {
    if size == 0 || size > MAX_COPY_FACT_BYTES { return vec![]; }
    let (Some(dst),Some(src))=(state.local(dst),state.local(src)) else {return vec![];};
    let Some(end)=src.checked_add(size) else {return vec![];};
    if end>state.bytes.len() || dst.checked_add(size).is_none_or(|e| e>state.bytes.len()) {return vec![];}
    state.slots.iter().filter_map(|(&offset,&fact)|
        (offset>=src && offset+8<=end).then(|| (dst+(offset-src),fact))).collect()
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
        self.charge(size.saturating_add(state.slots.len()))?;
        let Some(offset) = offset else {
            state.slots.clear();
            return if self.mode == Mode::Confined { Err(self.fail("unknown_pointer_write")) } else { Ok(()) };
        };
        let range = self.range(state, offset, size)?;
        state.slots.retain(|&start, _| start >= range.end || start + 8 <= range.start);
        if self.mode == Mode::Initialized { state.bytes[range].fill(true); }
        Ok(())
    }
    fn transfer(&mut self, state: &mut State, op: &Op, f: &Function) -> Result<(), Decline> {
        self.charge(1 + state.slots.len())?;
        // Snapshot memory-derived facts before overlapping stores/copies and
        // before aliased output registers are killed. No initial slot is known.
        let loaded = match *op {
            Op::Load { address, size: 8, .. } => state.local(address).and_then(|o| state.slots.get(&o).copied()),
            _ => None,
        };
        let mut stored = Vec::new();
        match *op {
            Op::Store {address,src,size:8} => {
                if let (Some(offset),Some(value)) = (state.local(address),state.facts[src as usize]) {
                    let value=match value {Fact::Constant(v)=>Fact::Constant(v as u64 as u128),v=>v};
                    stored.push((offset,value));
                }
            }
            Op::Copy {dst,src,size} => stored = copied_slots(state,dst,src,size),
            Op::CopyDynamic {dst,src,size} => {
                if let Some(size)=state.size(size) {stored=copied_slots(state,dst,src,size);}
            }
            _ => {},
        }
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
            _ => { self.unknown(state, "unknown_memory_effect")?; state.slots.clear(); },
        }
        for (offset,fact) in stored {
            // Positive writes above checked the complete destination extent.
            if state.slots.len() < MAX_SLOTS || state.slots.contains_key(&offset) {
                state.slots.insert(offset,fact);
            }
        }
        // Compute facts from the old inputs, then apply outputs in VM order.
        let mut outputs = vec![];
        match *op {
            Op::Load {dst,size:8,..} => { if let Some(fact)=loaded { outputs.push((dst,fact)); } },
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
        let state_bytes = f.frame_size.max(1).checked_add(MAX_SLOTS * 128)
            .and_then(|n| n.checked_add(f.registers.checked_mul(std::mem::size_of::<Option<Fact>>())
            ?)).ok_or_else(|| self.fail("state_limit"))?;
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
    fn run(&mut self, f: &Function) -> Result<(), Decline> {
        let blocks = self.blocks(f)?;
        let mut initial = State { bytes: vec![false; f.frame_size.max(1)], facts: vec![None; f.registers], slots: BTreeMap::new() };
        if self.mode == Mode::Initialized {
            for slot in &f.args { self.write(&mut initial, Some(slot.offset), slot.size)?; }
        }
        let state_work = f.frame_size.max(1) + f.registers + MAX_SLOTS;
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
                        let before=previous.slots.len();
                        previous.slots.retain(|offset,fact| state.slots.get(offset)==Some(fact));
                        changed |= before != previous.slots.len();
                        changed
                    }
                };
                if changed && !queued[next] { queued[next] = true; pending.push_back(next); }
            }
        }
        Ok(())
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
