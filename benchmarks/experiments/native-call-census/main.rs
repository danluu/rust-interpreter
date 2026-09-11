//! Typed opportunity census; does not execute guest code or predict speedup.
use bincode::Options;
pub use rust_interp_bytecode::*;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[allow(dead_code)]
mod emitter_support {
    use super::*;
    include!(concat!(env!("OUT_DIR"), "/support.rs"));
    pub fn mask(f: &Function) -> Vec<bool> {
        let fills = local_fills(f);
        f.code.iter().enumerate().map(|(pc, op)| supported(op) || fills.contains_key(&pc)).collect()
    }
}

#[path = "../../../crates/bytecode/src/calls.rs"]
mod calls;

#[derive(Deserialize)]
struct Profile { functions: Vec<FunctionCounts> }
#[derive(Deserialize)]
struct FunctionCounts {
    name: String,
    frame_size: usize,
    registers: usize,
    operations: Vec<String>,
    interpreted: Vec<u64>,
    jit_blocks: Vec<u64>,
    jit_block_ends: Vec<usize>,
}

fn frequencies(f: &Function, p: &FunctionCounts) -> Vec<u64> {
    assert_eq!(f.name, p.name);
    assert_eq!(f.frame_size, p.frame_size);
    assert_eq!(f.registers, p.registers);
    for len in [p.operations.len(), p.interpreted.len(), p.jit_blocks.len(), p.jit_block_ends.len()] {
        assert_eq!(f.code.len(), len);
    }
    // Whole-value identity guard only; names are not used for joining functions.
    assert!(f.code.iter().zip(&p.operations).all(|(op, text)| format!("{op:?}") == *text));
    let mut result = p.interpreted.clone();
    for (pc, &count) in p.jit_blocks.iter().enumerate() {
        if count == 0 { continue; }
        let end = p.jit_block_ends[pc];
        assert!(pc < end && end <= f.code.len());
        for value in &mut result[pc..end] { *value = value.checked_add(count).unwrap(); }
    }
    result
}

fn rejection(op: &Op) -> &'static str {
    // Descriptive categories only, called AFTER the actual emitter rejects an op.
    match op {
        Op::Call { .. } => "direct_call",
        Op::CallIndirect { .. } => "indirect_call",
        Op::Return => "return",
        Op::Trap { .. } => "trap",
        Op::Copy { .. } => "copy_size",
        Op::CopyDynamic { .. } => "dynamic_copy",
        Op::FillBytes { .. } => "unproven_fill",
        Op::Binary { .. } | Op::Unary { .. } => "integer_operation",
        Op::FloatBinary { .. } | Op::FloatUnary { .. } | Op::FloatConvert { .. } => "float_operation",
        Op::Switch { .. } => "switch_size",
        Op::Allocate { .. } | Op::Deallocate { .. } | Op::Reallocate { .. }
        | Op::CAllocate { .. } | Op::CDeallocate { .. } | Op::CReallocate { .. }
        | Op::CAlignedAllocate { .. } => "allocation",
        Op::ResetThreadLocals | Op::RegisterTlsDestructor { .. } => "tls",
        Op::RandomBytes { .. } | Op::CpuFeatureQuery { .. } => "host_operation",
        _ => "other_emitter_decline",
    }
}

// Remove functions depending on a rejected body. Cycles of otherwise supported
// direct calls remain included: this is a structural upper bound, not a proof
// of termination or that a leaf-only calling convention could run them.
fn closure(local: &[bool], edges: &[BTreeSet<usize>]) -> Vec<bool> {
    let mut allowed = local.to_vec();
    loop {
        let mut changed = false;
        for id in 0..allowed.len() {
            if allowed[id] && edges[id].iter().any(|&callee| !allowed[callee]) {
                allowed[id] = false;
                changed = true;
            }
        }
        if !changed { return allowed; }
    }
}

// For an acyclic leaf, even the sum of ALL body operations bounds every path.
// Include Return. Reject missing terminators and cycles, including unreachable
// cycles, conservatively. This is a virtual-instruction bound, not a time bound.
fn acyclic_bound(f: &Function) -> Option<u64> {
    if f.code.is_empty() { return None; }
    let mut edges = vec![Vec::new(); f.code.len()];
    let mut incoming = vec![0usize; f.code.len()];
    for (pc, op) in f.code.iter().enumerate() {
        match op {
            Op::Jump { target } => edges[pc].push(*target),
            Op::Switch { cases, otherwise, .. } => {
                edges[pc].push(*otherwise);
                edges[pc].extend(cases.iter().map(|(_, target)| *target));
            }
            Op::Return | Op::Trap { .. } => {}
            _ if pc + 1 < f.code.len() => edges[pc].push(pc + 1),
            _ => return None,
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
    (seen == f.code.len()).then_some(f.code.len() as u64)
}

// A prospective bound for fully prepared, acyclic direct-call trees. Each
// static Call already costs one in the body bound; add its callee's bound once
// per call site. Unresolved recursion and checked-add overflow remain excluded.
fn call_tree_bounds(functions: &[Function], local: &[bool]) -> Vec<Option<u64>> {
    let body: Vec<_> = functions.iter().zip(local)
        .map(|(f, &allowed)| if allowed { acyclic_bound(f) } else { None }).collect();
    let mut bounds = vec![None; functions.len()];
    loop {
        let mut changed = false;
        for (id, f) in functions.iter().enumerate() {
            if bounds[id].is_some() { continue; }
            let Some(mut total) = body[id] else { continue; };
            let mut complete = true;
            for op in &f.code {
                if let Op::Call { function, .. } = op {
                    match bounds[*function].and_then(|n| total.checked_add(n)) {
                        Some(n) => total = n,
                        None => { complete = false; break; }
                    }
                }
            }
            if complete { bounds[id] = Some(total); changed = true; }
        }
        if !changed { return bounds; }
    }
}

#[derive(Default, Serialize)]
struct Calls {
    sites: u64,
    calls: u128,
    proven_local_argument_calls: u128,
    frame_bytes_without_alignment_padding: u128,
    argument_copy_bytes: u128,
    result_copy_bytes: u128,
    register_slots: u128,
}
impl Calls {
    fn add(&mut self, n: u64, local: bool, f: &Function) {
        let n = n as u128;
        self.sites += 1;
        self.calls += n;
        if local { self.proven_local_argument_calls += n; }
        self.frame_bytes_without_alignment_padding += n * f.frame_size.max(1) as u128;
        self.argument_copy_bytes += n * f.args.iter().map(|a| a.size as u128).sum::<u128>();
        self.result_copy_bytes += n * f.result.size as u128;
        self.register_slots += n * f.registers as u128;
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    assert_eq!(args.len(), 2, "usage: native-call-census PROGRAM PROFILE");
    let bytes = std::fs::read(&args[0])?;
    assert!(bytes.len() <= 64 * 1024 * 1024);
    let program: Program = bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes)?;
    validate(&program)?;
    let profile: Profile = serde_json::from_reader(std::io::BufReader::new(std::fs::File::open(&args[1])?))?;
    assert_eq!(program.functions.len(), profile.functions.len());
    let masks: Vec<_> = program.functions.iter().map(emitter_support::mask).collect();
    let mut reasons = vec![BTreeMap::<&str, usize>::new(); program.functions.len()];
    let mut edges = vec![BTreeSet::new(); program.functions.len()];
    for (id, f) in program.functions.iter().enumerate() {
        for (pc, op) in f.code.iter().enumerate() {
            if let Op::Call { function, .. } = op { edges[id].insert(*function); }
            if !masks[id][pc] && !matches!(op, Op::Return) {
                *reasons[id].entry(rejection(op)).or_default() += 1;
            }
        }
    }
    let leaf: Vec<_> = reasons.iter().map(|r| r.is_empty()).collect();
    let bounds: Vec<_> = program.functions.iter().enumerate()
        .map(|(id, f)| if leaf[id] { acyclic_bound(f) } else { None }).collect();
    let local: Vec<_> = reasons.iter().map(|r| r.keys().all(|&k| k == "direct_call")).collect();
    let closed = closure(&local, &edges);
    // These groups explicitly require new terminal-trap and call/return
    // emission. They do not claim the current support predicate accepts Trap.
    let trap_leaf: Vec<_> = reasons.iter().map(|r| r.keys().all(|&k| k == "trap")).collect();
    let trap_local: Vec<_> = reasons.iter().map(|r| r.keys().all(|&k| matches!(k, "trap" | "direct_call"))).collect();
    let trap_closed = closure(&trap_local, &edges);
    let trap_bounds = call_tree_bounds(&program.functions, &trap_local);
    let proven = calls::local_arguments(&program);
    let mut groups: BTreeMap<_, _> = ["all_direct", "strict_leaf", "acyclic_strict_leaf",
        "locally_supported_with_direct_calls", "transitively_supported_with_direct_calls",
        "prospective_leaf_with_terminal_traps", "prospective_acyclic_leaf_with_terminal_traps",
        "prospective_direct_call_closure_with_terminal_traps", "prospective_bounded_call_tree_with_terminal_traps"]
        .into_iter().map(|name| (name, Calls::default())).collect();
    let mut rejected_call_weights = BTreeMap::<&str, u128>::new();
    let mut incoming: Vec<Calls> = (0..program.functions.len()).map(|_| Calls::default()).collect();
    let mut rows = Vec::new();
    let (mut instructions, mut indirect) = (0u128, 0u128);
    let mut self_ops = Vec::new();
    for (id, (f, p)) in program.functions.iter().zip(&profile.functions).enumerate() {
        let frequency = frequencies(f, p);
        let mut native_coverage = vec![false; f.code.len()];
        for (pc, &end) in p.jit_block_ends.iter().enumerate() {
            if end == 0 { continue; }
            assert!(pc < end && end <= f.code.len());
            native_coverage[pc..end].fill(true);
        }
        let total: u128 = frequency.iter().map(|&n| n as u128).sum();
        instructions += total;
        let mut unsupported = BTreeMap::<&str, u128>::new();
        let (mut short_ops, mut native_tail_ops) = (0u128, 0u128);
        for (pc, (op, &count)) in f.code.iter().zip(&frequency).enumerate() {
            if masks[id][pc] {
                if native_coverage[pc] { native_tail_ops += p.interpreted[pc] as u128; }
                else { short_ops += p.interpreted[pc] as u128; }
            } else { *unsupported.entry(rejection(op)).or_default() += count as u128; }
            match op {
                Op::Call { function: callee, .. } if count != 0 => {
                    assert_eq!(count, p.interpreted[pc]);
                    let target = &program.functions[*callee];
                    let is_local = proven[id][pc];
                    incoming[*callee].add(count, is_local, target);
                    for (name, included) in [("all_direct", true), ("strict_leaf", leaf[*callee]),
                        ("acyclic_strict_leaf", bounds[*callee].is_some()),
                        ("locally_supported_with_direct_calls", local[*callee]),
                        ("transitively_supported_with_direct_calls", closed[*callee]),
                        ("prospective_leaf_with_terminal_traps", trap_leaf[*callee]),
                        ("prospective_acyclic_leaf_with_terminal_traps", trap_leaf[*callee] && trap_bounds[*callee].is_some()),
                        ("prospective_direct_call_closure_with_terminal_traps", trap_closed[*callee]),
                        ("prospective_bounded_call_tree_with_terminal_traps", trap_bounds[*callee].is_some())] {
                        if included { groups.entry(name).or_default().add(count, is_local, target); }
                    }
                    for &reason in reasons[*callee].keys() {
                        *rejected_call_weights.entry(reason).or_default() += count as u128;
                    }
                }
                Op::CallIndirect { .. } => indirect += count as u128,
                _ => {}
            }
        }
        self_ops.push(serde_json::json!({
            "instructions": total,
            "jit_entries": p.jit_blocks.iter().map(|&n| n as u128).sum::<u128>(),
            "interpreted_operations": p.interpreted.iter().map(|&n| n as u128).sum::<u128>(),
            "supported_interpreted_without_emitted_region": short_ops,
            "supported_interpreted_inside_emitted_region": native_tail_ops,
            "unsupported_operation_counts": unsupported,
        }));
    }
    for (id, f) in program.functions.iter().enumerate() {
        if incoming[id].calls == 0 { continue; }
        rows.push(serde_json::json!({
            "id": id, "name": f.name, "frame_size": f.frame_size,
            "registers": f.registers, "operations": f.code.len(),
            "argument_sizes": f.args.iter().map(|a| a.size).collect::<Vec<_>>(),
            "result_size": f.result.size,
            "conservative_leaf_body_instruction_bound": bounds[id],
            "prospective_leaf_with_terminal_traps": trap_leaf[id],
            "prospective_direct_call_closure_with_terminal_traps": trap_closed[id],
            "prospective_whole_call_tree_instruction_bound": trap_bounds[id],
            "strict_leaf": leaf[id], "locally_supported_with_direct_calls": local[id],
            "transitively_supported_with_direct_calls": closed[id],
            "structural_rejections": reasons[id], "incoming_direct": incoming[id],
            "observed_self_work": self_ops[id],
        }));
    }
    rows.sort_by_key(|r| std::cmp::Reverse(r["incoming_direct"]["calls"].as_u64().unwrap()));
    println!("{}", serde_json::to_string_pretty(&serde_json::json!({
        "status": "Typed native-call eligibility census; no execution or transformation",
        "performance_measurement": false, "instructions": instructions,
        "groups": groups, "indirect_calls_without_target_attribution": indirect,
        "overlapping_structural_rejection_call_weights": rejected_call_weights,
        "callees": rows,
        "limitations": [
            "Counts and logical bytes are not time, predicted savings or a native-call implementation.",
            "Strict leaf allows Return as proposed ABI work; current JIT interprets Return.",
            "Acyclic strict leaf has a conservative whole-body virtual-instruction bound, excluding the caller's Call; it does not bound runtime or memory-copy time.",
            "Prospective groups need explicit native terminal-Trap support; no executed or unexecuted trap is silently ignored.",
            "Whole call-tree bounds require every target's code/storage to be ready before entry; otherwise a partial continuation or pre-entry fallback is still required.",
            "Eligibility checks the entire body, including untaken paths; traps and unsupported dead paths conservatively exclude it.",
            "Direct-call closure permits recursive cycles and assumes a broader ABI than leaf-only support.",
            "Short regions, exact budget tails, code capacity, initialization, aliases and fault continuations still require implementation.",
            "Observed self work includes any entries through indirect calls or TLS; those entries are not attributed to direct callers.",
            "Region coverage is observed profile metadata; unsupported-at-runtime and structural exclusions are distinct."
        ]
    }))?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn closure_preserves_cycles_and_propagates_rejection() {
        let edges = vec![[1].into(), [0].into(), [3].into(), [4].into(), [].into()];
        assert_eq!(closure(&[true, true, true, true, false], &edges), [true, true, false, false, false]);
    }
    #[test]
    fn actual_predicate_distinguishes_return_call_and_unproven_fill() {
        let mut f = Function { name: "census".into(), frame_size: 16, frame_align: 1,
            registers: 3, args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![
                Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 0 },
                Op::Imm { dst: 2, value: 16 }, Op::FillBytes { address: 0, value: 1, size: 2 },
                Op::Return,
            ] };
        assert_eq!(emitter_support::mask(&f), [true, true, true, true, false]);
        f.code.push(Op::Jump { target: 2 });
        assert!(!emitter_support::mask(&f)[3]);
        f.code[4] = Op::Call { function: 0, args: vec![], destination: 0 };
        assert!(!emitter_support::mask(&f)[4]);
    }
    #[test]
    fn whole_leaf_budget_bound_rejects_cycles_and_missing_terminators() {
        let mut f = Function { name: "bound".into(), frame_size: 1, frame_align: 1,
            registers: 1, args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![
                Op::Switch { value: 0, cases: vec![(0, 2), (1, 2)], otherwise: 1 },
                Op::Imm { dst: 0, value: 1 }, Op::Return,
            ] };
        assert_eq!(acyclic_bound(&f), Some(3));
        f.code[2] = Op::Jump { target: 0 };
        assert_eq!(acyclic_bound(&f), None);
        f.code[2] = Op::Imm { dst: 0, value: 2 };
        assert_eq!(acyclic_bound(&f), None);
        f.code = vec![Op::Return, Op::Jump { target: 1 }];
        assert_eq!(acyclic_bound(&f), None, "unreachable cycle excluded conservatively");
    }
    #[test]
    fn call_tree_counts_repeated_calls_and_rejects_recursion_and_blockers() {
        let make = |code| Function { name: "same display name".into(), frame_size: 1, frame_align: 1,
            registers: 1, args: vec![], result: Slot { offset: 0, size: 0 }, code };
        let call = |function| Op::Call { function, args: vec![], destination: 0 };
        let functions = vec![make(vec![call(1), call(1), Op::Return]),
            make(vec![Op::Trap { message: "terminal".into() }]),
            make(vec![call(3), Op::Return]), make(vec![call(2), Op::Return]),
            make(vec![call(5), Op::Return]), make(vec![Op::Return])];
        assert_eq!(call_tree_bounds(&functions, &[true, true, true, true, true, false]),
            [Some(5), Some(1), None, None, None, None]);
    }
}
