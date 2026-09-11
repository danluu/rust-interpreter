//! Conservative requirements for completely prepared native call trees.
use super::{local_fills, supported};
use crate::{Function, Op, Program};
use std::collections::VecDeque;

pub(super) const MAX_INSTRUCTIONS: u64 = 8192;
// Initial speculative-storage/host-nesting caps, not guest execution limits.
// A declined tree remains executable by the ordinary VM.
pub(super) const MAX_DEPTH: usize = 64;
pub(super) const MAX_FRAME_SPAN: usize = 256 * 1024;
pub(super) const MAX_REGISTER_SLOTS: usize = 64 * 1024;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Decline {
    UnsupportedOperation,
    MissingTerminator,
    ControlFlowCycle,
    CyclicDependency,
    UnavailableDependency,
    InstructionBound,
    DepthBound,
    StorageBound,
    ArithmeticOverflow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct Plan {
    /// Includes the root body's Return and every static nested Call/callee.
    /// Excludes the outer caller's Call instruction.
    pub instructions: u64,
    /// Includes this function's frame and register slice.
    pub depth: usize,
    pub frame_span: usize,
    pub register_slots: usize,
    pub frame_align: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct Requirements {
    pub root_base: usize,
    pub memory_end: usize,
    pub register_end: usize,
    pub frames: usize,
}

impl Plan {
    pub fn requirements(&self, active_memory: usize, active_registers: usize, active_frames: usize)
        -> Option<Requirements>
    {
        let root_base = active_memory.checked_add(self.frame_align - 1)? & !(self.frame_align - 1);
        Some(Requirements { root_base,
            memory_end: root_base.checked_add(self.frame_span)?,
            register_end: active_registers.checked_add(self.register_slots)?,
            frames: active_frames.checked_add(self.depth)?,
        })
    }
}

#[derive(Default)]
struct Pending {
    instructions: u64,
    children: usize,
    child_span: usize,
    child_registers: usize,
    child_depth: usize,
    child_align: usize,
}

impl Pending {
    fn add_child(&mut self, child: Plan) -> Result<(), Decline> {
        self.instructions = self.instructions.checked_add(child.instructions).ok_or(Decline::ArithmeticOverflow)?;
        if self.instructions > MAX_INSTRUCTIONS { return Err(Decline::InstructionBound); }
        self.child_span = self.child_span.max(child.frame_span);
        self.child_registers = self.child_registers.max(child.register_slots);
        self.child_depth = self.child_depth.max(child.depth);
        self.child_align = self.child_align.max(child.frame_align);
        self.children -= 1;
        Ok(())
    }

    fn finish(&self, function: &Function) -> Result<Plan, Decline> {
        // Returning a child leaves its aligned base as the parent's new live
        // end. All frame alignments are powers of two: successive child calls
        // can round that end no further than the largest child alignment.
        // Thus one (max alignment - 1) allowance per parent bounds ALL sibling
        // padding, followed by the maximum nested span. It must not be omitted.
        let frame_span = function.frame_size.max(1)
            .checked_add(self.child_align.max(1) - 1)
            .and_then(|n| n.checked_add(self.child_span)).ok_or(Decline::ArithmeticOverflow)?;
        let register_slots = function.registers.checked_add(self.child_registers).ok_or(Decline::ArithmeticOverflow)?;
        let depth = self.child_depth.checked_add(1).ok_or(Decline::ArithmeticOverflow)?;
        if depth > MAX_DEPTH { return Err(Decline::DepthBound); }
        if frame_span > MAX_FRAME_SPAN || register_slots > MAX_REGISTER_SLOTS { return Err(Decline::StorageBound); }
        Ok(Plan { instructions: self.instructions, depth, frame_span, register_slots,
                  frame_align: function.frame_align })
    }
}

/// Use only on validated programs, as with the ordinary region emitter.
/// Dependencies are processed once per static call site. This avoids repeated
/// full-program scans for deep call graphs and never recurses on the host stack.
pub(super) fn analyze(program: &Program) -> Vec<Result<Plan, Decline>> {
    let mut result = vec![None; program.functions.len()];
    let mut pending: Vec<Pending> = (0..program.functions.len()).map(|_| Pending::default()).collect();
    let mut parents = vec![Vec::new(); program.functions.len()];
    let mut queue = VecDeque::new();
    for (id, f) in program.functions.iter().enumerate() {
        let local = inspect_body(f);
        match local {
            Err(error) => { result[id] = Some(Err(error)); queue.push_back(id); }
            Ok(calls) => {
                pending[id].instructions = f.code.len() as u64;
                pending[id].children = calls.len();
                for callee in calls { parents[callee].push(id); }
                if pending[id].children == 0 {
                    result[id] = Some(pending[id].finish(f));
                    queue.push_back(id);
                }
            }
        }
    }
    while let Some(child) = queue.pop_front() {
        for &parent in &parents[child] {
            if result[parent].is_some() { continue; }
            let added = match result[child].expect("queued tree result") {
                Ok(plan) => pending[parent].add_child(plan),
                Err(_) => Err(Decline::UnavailableDependency),
            };
            let finished = match added {
                Err(error) => Some(Err(error)),
                Ok(()) if pending[parent].children == 0 => Some(pending[parent].finish(&program.functions[parent])),
                Ok(()) => None,
            };
            if let Some(value) = finished { result[parent] = Some(value); queue.push_back(parent); }
        }
    }
    result.into_iter().map(|entry| entry.unwrap_or(Err(Decline::CyclicDependency))).collect()
}

fn inspect_body(function: &Function) -> Result<Vec<usize>, Decline> {
    let n = function.code.len();
    if n as u64 > MAX_INSTRUCTIONS { return Err(Decline::InstructionBound); }
    if n == 0 { return Err(Decline::MissingTerminator); }
    let fills = local_fills(function);
    let mut edges = vec![Vec::new(); n];
    let mut incoming = vec![0usize; n];
    let mut calls = Vec::new();
    for (pc, op) in function.code.iter().enumerate() {
        if !supported(op) && !fills.contains_key(&pc) && !matches!(op, Op::Call { .. } | Op::Return | Op::Trap { .. }) {
            return Err(Decline::UnsupportedOperation);
        }
        if let Op::Call { function, .. } = op { calls.push(*function); }
        match op {
            Op::Jump { target } => edges[pc].push(*target),
            Op::Switch { cases, otherwise, .. } => {
                edges[pc].push(*otherwise);
                edges[pc].extend(cases.iter().map(|(_, target)| *target));
            }
            Op::Return | Op::Trap { .. } => {}
            _ if pc + 1 < n => edges[pc].push(pc + 1),
            _ => return Err(Decline::MissingTerminator),
        }
        for &target in &edges[pc] { incoming[target] += 1; }
    }
    let mut ready: Vec<_> = incoming.iter().enumerate().filter_map(|(pc, &n)| (n == 0).then_some(pc)).collect();
    let mut seen = 0;
    while let Some(pc) = ready.pop() {
        seen += 1;
        for &target in &edges[pc] {
            incoming[target] -= 1;
            if incoming[target] == 0 { ready.push(target); }
        }
    }
    if seen != n { return Err(Decline::ControlFlowCycle); }
    Ok(calls)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Slot, VERSION, Limits};

    fn function(size: usize, align: usize, code: Vec<Op>) -> Function {
        Function { name: "duplicate display name".into(), frame_size: size, frame_align: align,
            registers: 1, args: vec![], result: Slot { offset: 0, size: 0 }, code }
    }
    fn program(functions: Vec<Function>) -> Program {
        let p = Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
            functions, data: vec![0; 16], statics: vec![], thread_locals: vec![] };
        crate::validate(&p).unwrap();
        p
    }
    fn call(function: usize) -> Op { Op::Call { function, args: vec![], destination: 0 } }

    #[test]
    fn counts_every_call_site_and_uses_ids_not_names() {
        let p = program(vec![function(17, 16, vec![call(1), call(1), Op::Return]),
            function(32, 64, vec![Op::Return])]);
        let plans = analyze(&p);
        assert_eq!(plans[0], Ok(Plan { instructions: 5, depth: 2, frame_span: 112,
                                     register_slots: 2, frame_align: 16 }));
        assert_eq!(plans[0].unwrap().requirements(19, 3, 5),
            Some(Requirements { root_base: 32, memory_end: 144, register_end: 5, frames: 7 }));
        assert_eq!(crate::execute(&p, &[], Limits::default()).unwrap().instructions, 5);
        for input in [(usize::MAX, 0, 0), (16, usize::MAX, 0), (16, 0, usize::MAX)] {
            assert_eq!(plans[0].unwrap().requirements(input.0, input.1, input.2), None);
        }
    }

    #[test]
    fn bounds_real_nested_frame_peaks_including_sibling_padding() {
        for a in [1, 8, 16, 64, 128] {
            for b in [1, 8, 16, 64, 128] {
                for size in [0, 1, 15, 17, 63, 129] {
                    let p = program(vec![function(size, 16, vec![call(1), call(2), call(1), Op::Return]),
                        function(17, a, vec![call(3), Op::Return]),
                        function(33, b, vec![Op::Return]), function(31, 32, vec![Op::Return])]);
                    let plan = analyze(&p)[0].unwrap();
                    let requirement = plan.requirements(16, 0, 0).unwrap();
                    let result = crate::execute(&p, &[], Limits::default()).unwrap();
                    assert!(result.peak_memory <= requirement.memory_end, "{a} {b} {size}");
                    assert_eq!(result.instructions, plan.instructions);
                    assert_eq!(plan.depth, 3);
                }
            }
        }
    }

    #[test]
    fn cycles_and_unavailable_descendants_decline_without_recursing() {
        let p = program(vec![function(1, 1, vec![call(1), Op::Return]),
            function(1, 1, vec![call(0), Op::Return]),
            function(1, 1, vec![call(3), Op::Return]),
            function(1, 1, vec![Op::Jump { target: 0 }]),
            function(1, 1, vec![Op::Return, Op::Jump { target: 1 }]),
            function(1, 1, vec![Op::CopyDynamic { dst: 0, src: 0, size: 0 }, Op::Return])]);
        let plans = analyze(&p);
        assert_eq!(plans, [Err(Decline::CyclicDependency), Err(Decline::CyclicDependency),
            Err(Decline::UnavailableDependency), Err(Decline::ControlFlowCycle),
            Err(Decline::ControlFlowCycle), Err(Decline::UnsupportedOperation)]);
    }

    #[test]
    fn terminal_traps_and_actual_fill_proof_are_explicit() {
        let mut p = program(vec![function(16, 1, vec![Op::Trap { message: "real failure".into() }])]);
        assert_eq!(analyze(&p)[0].unwrap().instructions, 1);
        p.functions[0].registers = 3;
        p.functions[0].code = vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 0 },
            Op::Imm { dst: 2, value: 16 }, Op::FillBytes { address: 0, value: 1, size: 2 }, Op::Return];
        assert_eq!(analyze(&p)[0].unwrap().instructions, 5);
        p.functions[0].code.push(Op::Jump { target: 2 });
        assert_eq!(analyze(&p)[0], Err(Decline::UnsupportedOperation));
        p.functions[0].code = vec![Op::Imm { dst: 0, value: 1 }];
        assert_eq!(analyze(&p)[0], Err(Decline::MissingTerminator));
    }

    #[test]
    fn instruction_depth_and_storage_caps_keep_a_vm_fallback() {
        let mut p = program(vec![function(1, 1, vec![Op::Imm { dst: 0, value: 1 }; MAX_INSTRUCTIONS as usize])]);
        *p.functions[0].code.last_mut().unwrap() = Op::Return;
        assert_eq!(analyze(&p)[0].unwrap().instructions, MAX_INSTRUCTIONS);
        p.functions.push(function(1, 1, vec![Op::Return]));
        p.functions[0].code[0] = call(1);
        assert_eq!(analyze(&p)[0], Err(Decline::InstructionBound));
        let mut functions: Vec<_> = (0..=MAX_DEPTH).map(|i| function(1, 1,
            if i == MAX_DEPTH { vec![Op::Return] } else { vec![call(i + 1), Op::Return] })).collect();
        let deep = program(functions.clone());
        assert_eq!(analyze(&deep)[0], Err(Decline::DepthBound));
        assert_eq!(analyze(&deep)[1].unwrap().depth, MAX_DEPTH);
        assert_eq!(crate::execute(&deep, &[], Limits::default()).unwrap().instructions, (2 * MAX_DEPTH + 1) as u64);
        functions[0] = function(MAX_FRAME_SPAN + 1, 1, vec![Op::Return]);
        let large = program(functions);
        assert_eq!(analyze(&large)[0], Err(Decline::StorageBound));
        assert_eq!(crate::execute(&large, &[], Limits::default()).unwrap().instructions, 1);
    }
}
