//! Conservative direct-call closure for nonleaf expansion. Cycles, paths into
//! cycles and unknown indirect callees are excluded. Function IDs stay stable.
use crate::{Op, Program};

#[derive(Clone, Copy)]
pub(crate) struct CallFacts {
    pub(crate) nonrecursive: bool,
    // False only after a complete scan proves no direct call in this body.
    pub(crate) may_direct_call: bool,
}

pub(crate) fn call_facts(program: &Program) -> Vec<CallFacts> {
    analyze(program, 65_536, 500_000, 2_000_000)
}

fn analyze(program: &Program, functions: usize, edges: usize, operations: usize) -> Vec<CallFacts> {
    let n = program.functions.len();
    let unknown = || vec![CallFacts { nonrecursive: false, may_direct_call: true }; n];
    if n > functions { return unknown(); }
    let mut remaining = vec![0usize; n];
    let mut parents = vec![vec![]; n];
    let mut indirect = vec![false; n];
    let mut work = 0usize; let mut calls = 0usize;
    for (id, f) in program.functions.iter().enumerate() {
        for op in &f.code {
            work += 1; if work > operations { return unknown(); }
            match op {
                Op::Call { function, .. } => {
                    calls += 1; if calls > edges { return unknown(); }
                    remaining[id] += 1; parents[*function].push(id);
                }
                Op::CallIndirect { .. } => indirect[id] = true,
                _ => {}
            }
        }
    }
    let mut result = unknown();
    let mut todo: Vec<_> = (0..n).filter(|&id| {
        // Only the completed scan can prove absence, before counts are decremented.
        result[id].may_direct_call = remaining[id] != 0;
        remaining[id] == 0 && !indirect[id]
    }).collect();
    while let Some(id) = todo.pop() {
        result[id].nonrecursive = true;
        for &parent in &parents[id] {
            remaining[parent] -= 1;
            if remaining[parent] == 0 && !indirect[parent] { todo.push(parent); }
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Function, Slot, VERSION};
    fn graph(targets: &[Vec<usize>]) -> Program {
        Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
            data: vec![], statics: vec![], thread_locals: vec![], functions: targets.iter().enumerate().map(|(id, targets)|
                Function { name: format!("node-{id}"), frame_size: 1, frame_align: 1, registers: 1,
                    args: vec![], result: Slot { offset: 0, size: 0 },
                    code: std::iter::once(Op::Local { dst: 0, offset: 0 })
                        .chain(targets.iter().map(|&function| Op::Call { function, args: vec![], destination: 0 }))
                        .chain([Op::Return]).collect() }).collect() }
    }
    #[test]
    fn cycles_unknown_edges_and_duplicate_children_are_handled() {
        let mut p = graph(&[vec![1], vec![2], vec![1], vec![4,4], vec![], vec![3]]);
        crate::validate(&p).unwrap();
        let facts = call_facts(&p);
        assert_eq!(facts.iter().map(|f| f.nonrecursive).collect::<Vec<_>>(), [false,false,false,true,true,true]);
        assert_eq!(facts.iter().map(|f| f.may_direct_call).collect::<Vec<_>>(), [true,true,true,true,false,true]);
        p.functions[4].code.insert(1, Op::CallIndirect { callee: 0, args: vec![], arg_sizes: vec![], destination: 0, result_size: 0 });
        crate::validate(&p).unwrap();
        let facts = call_facts(&p);
        assert_eq!(facts.iter().map(|f| f.nonrecursive).collect::<Vec<_>>(), [false;6]);
        assert_eq!(facts.iter().map(|f| f.may_direct_call).collect::<Vec<_>>(), [true,true,true,true,false,true]);
    }
    #[test]
    fn graph_bounds_decline_without_partial_results() {
        let p = graph(&[vec![1], vec![]]);
        let facts = call_facts(&p);
        assert_eq!(facts.iter().map(|f| f.nonrecursive).collect::<Vec<_>>(), [true,true]);
        assert_eq!(facts.iter().map(|f| f.may_direct_call).collect::<Vec<_>>(), [true,false]);
        for (f,e,o) in [(1,1,5),(2,0,5),(2,1,4)] {
            let facts = analyze(&p,f,e,o);
            assert_eq!(facts.iter().map(|f| f.nonrecursive).collect::<Vec<_>>(), [false,false]);
            assert_eq!(facts.iter().map(|f| f.may_direct_call).collect::<Vec<_>>(), [true,true]);
        }
        let facts = analyze(&p,2,1,5);
        assert_eq!(facts.iter().map(|f| f.nonrecursive).collect::<Vec<_>>(), [true,true]);
        assert_eq!(facts.iter().map(|f| f.may_direct_call).collect::<Vec<_>>(), [true,false]);
    }
}
