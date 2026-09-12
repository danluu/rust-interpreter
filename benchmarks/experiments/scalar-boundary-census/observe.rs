//! Typed diagnostics only. Never mutates lowered operations or allocation state.
use super::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

const MAX_ROWS: usize = 32_768;
const MAX_FUNCTIONS: usize = 10_000;

#[derive(Default)]
pub(crate) struct Collector {
    functions: Vec<Observation>,
    rows: usize,
}

impl Collector {
    pub(crate) fn remaining(&self) -> usize { MAX_ROWS - self.rows }
    pub(crate) fn push(&mut self, value: Observation) -> Result<()> {
        if self.functions.len() >= MAX_FUNCTIONS || value.rows.len() > self.remaining() {
            return Err("scalar boundary collector bound exceeded".into());
        }
        self.rows += value.rows.len();
        self.functions.push(value);
        Ok(())
    }
}

pub(crate) struct Observation {
    id: usize,
    args: Vec<Slot>,
    result: Slot,
    status: &'static str,
    rows: Vec<Value>,
    private_primitive_locals: usize,
    spread_argument: bool,
    synthetic_caller_location: bool,
}

fn within_bounds(locals: usize, operations: usize, arguments: usize, remaining: usize) -> bool {
    locals <= 4096 && operations <= 100_000 && arguments.checked_add(1).is_some_and(|n| n <= remaining)
}

fn width(size: usize) -> bool { matches!(size, 1 | 2 | 4 | 8 | 16) }
fn slot_key(slot: &Slot) -> (usize, usize) { (slot.offset, slot.size) }

// Mirror the promoter's colored-slot rule: merge exact ranges, intersect
// eligibility, then exclude partial overlaps. Bounds keep the sort small.
fn disjoint_private(slots: &[Slot], private: &[bool]) -> Result<Vec<bool>> {
    if slots.len() != private.len() { return Err("scalar boundary slot count differs".into()); }
    let mut merged = BTreeMap::<(usize, usize), bool>::new();
    for (slot, yes) in slots.iter().zip(private) {
        if slot.size != 0 { *merged.entry((slot.offset, slot.size)).or_insert(true) &= yes; }
    }
    let ranges: Vec<_> = merged.into_iter().collect();
    let mut allowed = BTreeSet::new();
    let mut prefix_end = 0;
    for (i, &((offset, size), yes)) in ranges.iter().enumerate() {
        let end = offset.checked_add(size).ok_or("scalar boundary range overflow")?;
        if yes && prefix_end <= offset && ranges.get(i+1).is_none_or(|&((next, _), _)| next >= end) {
            allowed.insert((offset, size));
        }
        prefix_end = prefix_end.max(end);
    }
    Ok(slots.iter().map(|s| allowed.contains(&(s.offset, s.size))).collect())
}

fn reasons(context: bool, call: bool, aggregate: bool, disjoint: bool, size: usize, spread: bool) -> Vec<&'static str> {
    let mut out = vec![];
    if !context { out.push("use_context_or_address_exposure"); }
    if !call { out.push("call_operand"); }
    if !aggregate { out.push("aggregate_operand"); }
    if context && call && aggregate && !disjoint && size != 0 { out.push("overlapping_or_shared_storage"); }
    if !width(size) { out.push("zero_or_unsupported_width"); }
    if spread { out.push("spread_argument"); }
    out
}

pub(crate) fn capture(lower: &Lower<'_, '_>, arguments: &[Slot], remaining: usize) -> Result<Observation> {
    let mut out = Observation {
        id: lower.exporter.trace_function.ok_or("missing scalar boundary function identity")?,
        args: arguments.to_vec(), result: lower.locals[0], status: "observed", rows: vec![],
        private_primitive_locals: 0, spread_argument: lower.body.spread_arg.is_some(),
        synthetic_caller_location: lower.caller_location.is_some(),
    };
    if !within_bounds(lower.locals.len(), lower.code.len(), lower.body.arg_count, remaining) {
        out.status = "analysis_bound_exceeded";
        return Ok(out);
    }
    let n = lower.locals.len();
    let mut context = vec![true; n];
    let mut call = vec![true; n];
    let mut aggregate = vec![true; n];
    for (bb, block) in lower.body.basic_blocks.iter_enumerated() {
        for (statement_index, statement) in block.statements.iter().enumerate() {
            Uses { eligible: &mut context }.visit_statement(statement, mir::Location { block: bb, statement_index });
            if let StatementKind::Assign(assignment) = &statement.kind {
                if let Rvalue::Aggregate(_, ops) = &assignment.1 {
                    for op in ops { exclude_operand(&mut aggregate, op); }
                }
            }
        }
        Uses { eligible: &mut context }.visit_terminator(block.terminator(), mir::Location { block: bb, statement_index: block.statements.len() });
        if let TerminatorKind::Call { args, .. } = &block.terminator().kind {
            for arg in args { exclude_operand(&mut call, &arg.node); }
        }
    }
    let private: Vec<_> = (0..n).map(|i| context[i] && call[i] && aggregate[i]).collect();
    let disjoint = disjoint_private(&lower.locals, &private)?;
    let mut primitive_private = vec![false; n];
    for (local, decl) in lower.body.local_decls.iter_enumerated() {
        let id = local.as_usize();
        let ty = lower.mono(decl.ty);
        let primitive = matches!(ty.kind(), ty::Int(_) | ty::Uint(_) | ty::Float(_) | ty::Bool | ty::Char);
        primitive_private[id] = id > lower.body.arg_count && primitive && private[id];
        if id > lower.body.arg_count { continue; }
        let slot = lower.locals[id];
        let scalar_layout = matches!(lower.layout(ty)?.backend_repr, rustc_abi::BackendRepr::Scalar(_));
        let spread = Some(local) == lower.body.spread_arg;
        let rejected = reasons(context[id], call[id], aggregate[id], disjoint[id], slot.size, spread);
        let matches: Vec<_> = arguments.iter().enumerate().filter_map(|(i, s)| (slot_key(s) == slot_key(&slot)).then_some(i)).collect();
        let binding = id == 0 || (slot.size != 0 && !spread && matches.len() == 1);
        out.rows.push(json!({"local": id, "role": if id == 0 {"result"} else {"argument"},
            "slot": slot, "primitive": primitive, "scalar_layout": scalar_layout,
            "private_use_context": context[id], "private_call_operand": call[id],
            "private_aggregate_operand": aggregate[id], "disjoint_private_storage": disjoint[id],
            "abi_argument_indices": if id == 0 {vec![]} else {matches}, "abi_binding": binding,
            "eligible_primitive": primitive && binding && rejected.is_empty(),
            "eligible_scalar_layout": scalar_layout && binding && rejected.is_empty(), "rejections": rejected}));
    }
    // Reproduce the ordinary primitive selector separately, including colored
    // range eligibility. Its slots may move later; do not publish PC mappings.
    let primitive_disjoint = disjoint_private(&lower.locals, &primitive_private)?;
    let slots: BTreeSet<_> = lower.locals.iter().enumerate().filter(|(i, s)| primitive_disjoint[*i] && width(s.size))
        .map(|(_, s)| (s.offset, s.size)).collect();
    out.private_primitive_locals = slots.len();
    Ok(out)
}

fn bind(value: Observation, functions: &[Function]) -> Result<Value> {
    let f = functions.get(value.id).ok_or("scalar boundary function ID out of range")?;
    if !f.args.iter().map(slot_key).eq(value.args.iter().map(slot_key)) || slot_key(&f.result) != slot_key(&value.result) {
        return Err("scalar boundary ABI changed after observation".into());
    }
    let digest = format!("{:x}", Sha256::digest(bincode::serialize(f).map_err(|e| e.to_string())?));
    Ok(json!({"function_id": value.id, "function_sha256": digest,
        "args": f.args, "result": f.result, "status": value.status, "rows": value.rows,
        "ordinary_private_primitive_slots": value.private_primitive_locals,
        "spread_argument": value.spread_argument, "synthetic_caller_location": value.synthetic_caller_location}))
}

pub(crate) fn report(collector: Collector, program: &Program) -> Result<()> {
    let mut seen = BTreeSet::new();
    let mut functions = vec![];
    for observation in collector.functions {
        if !seen.insert(observation.id) { return Err("duplicate scalar boundary function ID".into()); }
        functions.push(bind(observation, &program.functions)?);
    }
    functions.sort_by_key(|f| f["function_id"].as_u64().unwrap());
    let encoded = serde_json::to_string(&json!({"schema_version": 1, "diagnostic_only": true,
        "max_rows": MAX_ROWS, "max_functions": MAX_FUNCTIONS, "boundary_rows": collector.rows,
        "program_functions": program.functions.len(), "functions": functions})).map_err(|e| e.to_string())?;
    if encoded.len() > 32 * 1024 * 1024 { return Err("scalar boundary report byte bound exceeded".into()); }
    eprintln!("rust-interp-scalar-boundary: {encoded}");
    Ok(())
}

#[cfg(test)]
#[path="scalar_boundary_tests.rs"]
mod tests;
