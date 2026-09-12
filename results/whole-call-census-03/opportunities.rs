use super::{CallSite, Function, Op, Program, Slot, registers};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};

fn disjoint(slots: impl Iterator<Item = Slot>) -> bool {
    let mut ranges: Vec<_> = slots.filter(|s| s.size != 0)
        .map(|s| (s.offset, s.offset + s.size)).collect();
    ranges.sort_unstable();
    ranges.windows(2).all(|p| p[0].1 <= p[1].0)
}

// Diagnostic proposal: exactly one call, Local address definitions, then one
// complete result copy. No loads, stores, argument regrouping or control flow.
// The production pass's direct-result form is deliberately excluded here.
fn result_copy_target(program: &Program, id: usize) -> Option<usize> {
    let f = &program.functions[id];
    let pc = f.code.iter().position(|op| matches!(op, Op::Call { .. }))?;
    let Op::Call { function, args, destination } = &f.code[pc] else { return None };
    let [suffix @ .., Op::Copy { dst, src, size }, Op::Return] = &f.code[pc + 1..] else { return None };
    if !f.code[..pc].iter().chain(suffix).all(|op| matches!(op, Op::Local { .. }))
        || *size == 0 || *size != f.result.size { return None; }
    let callee = &program.functions[*function];
    if f.args.len() != args.len() || f.args.len() != callee.args.len()
        || f.result.size != callee.result.size
        || f.args.iter().zip(&callee.args).any(|(a, b)| a.size != b.size) { return None; }
    let mut locals = BTreeMap::new();
    for op in &f.code[..pc] {
        if let Op::Local { dst, offset } = op { locals.insert(*dst, *offset); }
    }
    if args.iter().zip(&f.args).any(|(r, s)| locals.get(r) != Some(&s.offset)) { return None; }
    let temporary = *locals.get(destination)?;
    if temporary.checked_add(*size)? > f.frame_size
        || !disjoint(f.args.iter().copied().chain([f.result, Slot { offset: temporary, size: *size }])) {
        return None;
    }
    for op in suffix {
        if let Op::Local { dst, offset } = op { locals.insert(*dst, *offset); }
    }
    (locals.get(dst) == Some(&f.result.offset) && locals.get(src) == Some(&temporary)).then_some(*function)
}

fn leaf_reasons(f: &Function) -> Vec<&'static str> {
    let mut reasons = BTreeSet::new();
    if f.code.len() <= 1 || !f.code.iter().any(|op| matches!(op, Op::Return))
        || !matches!(f.code.last(), Some(Op::Return | Op::Trap { .. } | Op::Jump { .. } | Op::Switch { .. })) {
        reasons.insert("body_shape");
    }
    if f.code.len() > 192 { reasons.insert("operations_over_192"); }
    if f.frame_size > 512 { reasons.insert("frame_over_512"); }
    if f.registers > 256 { reasons.insert("registers_over_256"); }
    if f.result.size > 128 || f.args.iter().any(|s| s.size > 128) { reasons.insert("abi_over_128"); }
    if registers::needs_initial_zeroes_for_inlining(f) { reasons.insert("register_initialization"); }
    for op in &f.code {
        let reason = match op {
            Op::Imm { .. } | Op::Local { .. } | Op::Load { .. } | Op::Store { .. }
            | Op::Cast { .. } | Op::Select { .. } | Op::Assert { .. } | Op::Jump { .. }
            | Op::Return | Op::Trap { .. } => None,
            Op::Copy { size, .. } => (*size > 128).then_some("copy_over_128"),
            Op::Binary { bits, .. } | Op::Unary { bits, .. } => (*bits > 64).then_some("integer_over_64"),
            Op::Switch { cases, .. } => (cases.len() > 16).then_some("switch_over_16"),
            Op::CompareBytes { .. } => Some("compare_bytes"),
            Op::Call { .. } => Some("direct_call"),
            Op::FillBytes { .. } => Some("fill_bytes"),
            _ => Some("other_opcode"),
        };
        if let Some(reason) = reason { reasons.insert(reason); }
    }
    reasons.into_iter().collect()
}

pub(super) fn inspect(program: &Program, sites: &[CallSite]) -> Result<Value, String> {
    let mut incoming = vec![0u128; program.functions.len()];
    let mut native = incoming.clone();
    let mut local = incoming.clone();
    let mut site_count = vec![0usize; incoming.len()];
    for s in sites {
        if let Some(callee) = s.callee {
            incoming[callee] += s.native as u128 + s.interpreted as u128;
            native[callee] += s.native as u128;
            site_count[callee] += 1;
            if s.local_result && s.local_arguments.iter().all(|x| *x) {
                local[callee] += s.native as u128 + s.interpreted as u128;
            }
        }
    }
    let next: Vec<_> = (0..program.functions.len()).map(|id| result_copy_target(program, id)).collect();
    let mut wrappers = vec![];
    let mut ranked = vec![];
    let mut weighted_reasons = BTreeMap::<&str, u128>::new();
    let mut compare_only = 0u128;
    let mut eligible = 0u128;
    let mut prefix_only = 0u128;
    let mut compare_or_prefix = 0u128;
    let mut wrapper_calls = 0u128;
    let mut wrapper_frames = 0u128;
    for (id, f) in program.functions.iter().enumerate() {
        let reasons = leaf_reasons(f);
        let prefix_suffices = !registers::needs_initial_zeroes(f);
        for reason in &reasons { *weighted_reasons.entry(reason).or_default() += incoming[id]; }
        if reasons.is_empty() { eligible += incoming[id]; }
        if reasons == ["compare_bytes"] { compare_only += incoming[id]; }
        if reasons == ["register_initialization"] && prefix_suffices { prefix_only += incoming[id]; }
        if !reasons.is_empty() && reasons.iter().all(|r| *r == "compare_bytes"
            || (*r == "register_initialization" && prefix_suffices)) {
            compare_or_prefix += incoming[id];
        }
        if let Some(target) = next[id] {
            // A diagnostic cycle exclusion, bounded by the function count.
            let mut seen = BTreeSet::new();
            let mut current = id;
            while seen.insert(current) {
                match next[current] { Some(n) => current = n, None => break }
            }
            if next[current].is_none() {
                wrapper_calls += incoming[id];
                wrapper_frames += incoming[id] * f.frame_size as u128;
                wrappers.push(json!({"function":id,"target":target,"name":f.name,
                    "incoming_calls":incoming[id],"native_incoming_calls":native[id],
                    "frame_size":f.frame_size,"operations":f.code.len(),
                    "args":f.args,"result":f.result}));
            }
        }
        if incoming[id] != 0 {
            ranked.push((incoming[id], json!({"function":id,"name":f.name,
                "incoming_calls":incoming[id],"native_incoming_calls":native[id],
                "caller_local_calls":local[id],"executed_incoming_sites":site_count[id],
                "frame_size":f.frame_size,"registers":f.registers,"operations":f.code.len(),
                "leaf_rejections":reasons,"entry_prefix_initialization_suffices":prefix_suffices,
                "args":f.args,"result":f.result})));
        }
    }
    ranked.sort_by(|a,b| b.0.cmp(&a.0));
    Ok(json!({"result_copy_wrappers":wrappers,"result_copy_wrapper_calls":wrapper_calls,
        "result_copy_wrapper_frame_bytes":wrapper_frames,"compare_bytes_only_calls":compare_only,
        "entry_prefix_only_calls":prefix_only,"compare_or_prefix_calls":compare_or_prefix,
        "existing_leaf_eligible_calls":eligible,"weighted_leaf_rejections_nonexclusive":weighted_reasons,
        "top_callees":ranked.into_iter().take(50).map(|(_,v)|v).collect::<Vec<_>>(),
        "limitation":"Eligibility is a necessary condition; caller placement, code growth and initialization guards still apply. Counts do not predict wall time."}))
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Program {
        let slot = |offset| Slot { offset, size: 1 };
        let mut p = Program { version: rust_interp_bytecode::VERSION, target: "aarch64-apple-darwin".into(),
            entry: 0, functions: vec![], data: vec![], statics: vec![], thread_locals: vec![] };
        let f = Function { name: "wrapper".into(), frame_size: 4, frame_align: 1,
            registers: 4, args: vec![slot(1)], result: slot(0), code: vec![
                Op::Local { dst: 0, offset: 1 }, Op::Local { dst: 1, offset: 2 },
                Op::Call { function: 1, args: vec![0], destination: 1 },
                Op::Local { dst: 2, offset: 0 }, Op::Local { dst: 3, offset: 2 },
                Op::Copy { dst: 2, src: 3, size: 1 }, Op::Return ] };
        let mut callee = f.clone(); callee.name = "callee".into(); callee.code = vec![Op::Return];
        p.functions = vec![f, callee]; p
    }
    #[test]
    fn exact_copy_wrapper_is_recognized() {
        let p = fixture(); super::super::validate(&p).unwrap();
        assert_eq!(result_copy_target(&p, 0), Some(1));
        assert_eq!(result_copy_target(&p, 1), None);
    }
    #[test]
    fn partial_alias_and_redefinition_are_rejected() {
        for (pc, op) in [(5, Op::Copy { dst: 2, src: 3, size: 0 }),
            (1, Op::Local { dst: 1, offset: 1 }), (4, Op::Local { dst: 3, offset: 1 }),
            (0, Op::Local { dst: 0, offset: 0 }), (3, Op::Local { dst: 2, offset: 1 })] {
            let mut p = fixture(); p.functions[0].code[pc] = op;
            assert_eq!(result_copy_target(&p, 0), None);
        }
    }
    #[test]
    fn side_effects_and_changed_abi_are_rejected() {
        let mut p = fixture(); p.functions[0].code.insert(3, Op::Store { address: 0, src: 1, size: 1 });
        assert_eq!(result_copy_target(&p, 0), None);
        let mut p = fixture(); p.functions[1].args[0].size = 2;
        assert_eq!(result_copy_target(&p, 0), None);
    }
    #[test]
    fn compare_bytes_and_cycles_are_reported_separately() {
        let mut p = fixture();
        p.functions[1].code = vec![Op::Imm { dst: 0, value: 0 },
            Op::CompareBytes { dst: 1, left: 0, right: 0, size: 0 }, Op::Return];
        assert_eq!(leaf_reasons(&p.functions[1]), vec!["compare_bytes"]);
        p.functions[1] = p.functions[0].clone();
        if let Op::Call { function, .. } = &mut p.functions[1].code[2] { *function = 0; }
        assert!(inspect(&p, &[]).unwrap()["result_copy_wrappers"].as_array().unwrap().is_empty());
    }
}
