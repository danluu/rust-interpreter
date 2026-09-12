//! Diagnostic child of scalar_frame. Never changes production slots or code.
use super::*;

#[derive(Clone, Copy, Debug, PartialEq)]
enum Fact { Local(usize), Immediate(u128) }
#[derive(Clone, Debug, Default, serde::Serialize, serde::Deserialize)]
struct Coverage {
    writes: Vec<(usize, usize)>,
    reads: Vec<(usize, usize)>,
    calls: Vec<(usize, usize, Vec<Option<usize>>)>, // resolve byte ABI after lowering
    straight: bool,
}
impl Coverage {
    fn complete(&self, slot: Slot, program: &Program) -> bool {
        if !self.straight { return false; }
        let Some(end) = slot.offset.checked_add(slot.size) else { return false; };
        let mut ranges = self.writes.clone();
        let mut reads = self.reads.clone();
        for (callee, offset, arguments) in &self.calls {
            let Some(f) = program.functions.get(*callee) else { return false; };
            if arguments.len() != f.args.len() { return false; }
            ranges.push((*offset, f.result.size));
            for (argument, slot) in arguments.iter().zip(&f.args) {
                if let Some(at) = argument { reads.push((*at, slot.size)); }
            }
        }
        // Lowering may introduce a read/modify/write absent from a whole-place
        // MIR Store event (for example a niche discriminant). Conservatively
        // preserve input liveness for every emitted read of this slot, even
        // when an earlier emitted store would already initialize it.
        if reads.iter().any(|&(at, size)| size != 0 && at < end &&
            at.saturating_add(size) > slot.offset) { return false; }
        ranges.sort_unstable();
        let mut covered = slot.offset;
        for (offset, size) in ranges {
            let Some(limit) = offset.checked_add(size) else { return false; };
            if offset > covered { break; }
            if limit > covered { covered = limit; }
            if covered >= end { return true; }
        }
        slot.size == 0
    }
}

fn coverage(code: &[Op], registers: usize) -> Coverage {
    if code.len() > MAX_EVENTS || registers > 1_000_000 { return Coverage::default(); }
    let mut facts = BTreeMap::<Reg, Fact>::new();
    let mut result = Coverage { straight: true, ..Coverage::default() };
    for (pc, op) in code.iter().enumerate() {
        if matches!(op, Op::Switch {..} | Op::Return | Op::Trap {..}) ||
            (matches!(op, Op::Jump {..}) && pc + 1 != code.len()) {
            result.straight = false;
            return result;
        }
        let local = |r: Reg| match facts.get(&r).copied() { Some(Fact::Local(x)) => Some(x), _ => None };
        let immediate = |r: Reg| match facts.get(&r).copied() { Some(Fact::Immediate(x)) => Some(x), _ => None };
        match op {
            Op::Load { address, size, .. } => if let Some(at) = local(*address) { result.reads.push((at, usize::from(*size))); },
            Op::Store { address, size, .. } => if let Some(at) = local(*address) { result.writes.push((at, usize::from(*size))); },
            Op::Copy { dst, src, size } => {
                if let Some(at) = local(*dst) { result.writes.push((at, *size)); }
                if let Some(at) = local(*src) { result.reads.push((at, *size)); }
            },
            Op::CopyDynamic { src, size, .. } => if let Some(at) = local(*src) {
                result.reads.push((at, immediate(*size).and_then(|n| usize::try_from(n).ok()).unwrap_or(usize::MAX)));
            },
            Op::CompareBytes { left, right, size, .. } => for r in [left, right] {
                if let Some(at) = local(*r) { result.reads.push((at, immediate(*size).and_then(|n| usize::try_from(n).ok()).unwrap_or(usize::MAX))); }
            },
            Op::FillBytes { address, size, .. } => if let (Some(at), Some(n)) = (local(*address), immediate(*size)) {
                if let Ok(n) = usize::try_from(n) { result.writes.push((at, n)); }
            },
            Op::Call { function, destination, args } => if let Some(at) = local(*destination) {
                result.calls.push((*function, at, args.iter().map(|r| local(*r)).collect()));
            } else { return Coverage::default(); },
            Op::CallIndirect { destination, result_size, args, arg_sizes, .. } => {
                if let Some(at) = local(*destination) { result.writes.push((at, *result_size)); }
                for (r, size) in args.iter().zip(arg_sizes) { if let Some(at) = local(*r) { result.reads.push((at, *size)); } }
            },
            _ => {},
        }
        let output = match op {
            Op::Local { dst, offset } => Some((*dst, Fact::Local(*offset))),
            Op::Imm { dst, value } => Some((*dst, Fact::Immediate(*value))),
            Op::Binary { dst, overflow, op: Binary::Add, a, b, bits: 64, signed: false } if dst != overflow => {
                let parts = local(*a).zip(immediate(*b)).or_else(|| local(*b).zip(immediate(*a)));
                parts.and_then(|(at, n)| usize::try_from(n).ok().and_then(|n| at.checked_add(n)))
                    .map(|at| (*dst, Fact::Local(at)))
            },
            _ => None,
        };
        // The retained exhaustive visitor prevents stale facts across every
        // register writer, including aliased outputs and indirect operations.
        rust_interp_bytecode::diagnostic_visit_registers(op, |_| {}, |r| {
            facts.remove(&r);
        });
        if let Some((r, value)) = output {
            if (r as usize) < registers { facts.insert(r, value); }
        }
    }
    result
}

struct ByteUses<'a> {
    reasons: &'a mut [Option<&'static str>],
    event: Event,
}
impl ByteUses<'_> {
    fn access(&mut self, i: usize, context: PlaceContext, projected: bool, dereference: bool) {
        if dereference {
            // A write/borrow through a pointer reads its value; it does not
            // address or overwrite the pointer's own storage.
            self.event.reads.insert(i);
            return;
        }
        match context {
            PlaceContext::NonUse(..) => {},
            PlaceContext::NonMutatingUse(NonMutatingUseContext::Copy | NonMutatingUseContext::Move | NonMutatingUseContext::Inspect) => {
                self.event.reads.insert(i);
            },
            PlaceContext::MutatingUse(MutatingUseContext::Store) => {
                self.event.writes.insert(i);
                if projected { self.event.reads.insert(i); }
            },
            // Apply destination writes only on the normal successor edge.
            PlaceContext::MutatingUse(MutatingUseContext::Call) => {},
            _ => {
                self.reasons[i].get_or_insert("address_or_unsupported_context");
                self.event.reads.insert(i);
            },
        }
    }
}
impl<'tcx> Visitor<'tcx> for ByteUses<'_> {
    fn visit_place(&mut self, place: &Place<'tcx>, context: PlaceContext, _: mir::Location) {
        for projection in place.projection {
            if let mir::ProjectionElem::Index(index) = projection { self.event.reads.insert(index.as_usize()); }
        }
        let dereference = place.projection.iter().any(|p| matches!(p, mir::ProjectionElem::Deref));
        self.access(place.local.as_usize(), context, !place.projection.is_empty(), dereference);
    }
    fn visit_local(&mut self, local: mir::Local, context: PlaceContext, _: mir::Location) {
        self.access(local.as_usize(), context, false, false);
    }
}

pub(crate) fn remember(lower: &mut Lower<'_, '_>, block: usize, event: usize, start: usize) {
    if let Some(slot) = lower.byte_spans.get_mut(block).and_then(|b| b.get_mut(event)) {
        *slot = Some((start, lower.code.len()));
    }
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
struct Write { block: usize, event: usize, local: usize, coverage: Coverage }
#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub(crate) struct Observation {
    id: usize,
    name: String,
    origins: BTreeMap<Reg,usize>,
    abi_count: usize,
    capture_nanos: u128,
    extent: usize,
    slots: Vec<Slot>,
    shapes: Vec<(usize, usize)>,
    #[serde(deserialize_with = "owned_reasons")]
    reasons: Vec<Option<&'static str>>,
    events: Vec<Vec<Event>>,
    successors: Vec<Vec<usize>>,
    writes: Vec<Write>,
    baseline: bool,
    #[serde(deserialize_with = "owned_reason")]
    decline: Option<&'static str>,
}

// Cache decoding retains only this closed diagnostic vocabulary. It never
// interns or leaks a string supplied by the payload.
fn reason(value: Option<String>) -> std::result::Result<Option<&'static str>, String> {
    match value.as_deref() {
        None => Ok(None),
        Some("abi") => Ok(Some("abi")),
        Some("zero_size") => Ok(Some("zero_size")),
        Some("address_or_unsupported_context") => Ok(Some("address_or_unsupported_context")),
        Some("origin_bound") => Ok(Some("origin_bound")),
        Some("input_bound") => Ok(Some("input_bound")),
        _ => Err("unknown frame observation reason".into()),
    }
}
fn owned_reason<'de, D: serde::Deserializer<'de>>(d: D) -> std::result::Result<Option<&'static str>, D::Error> {
    use serde::Deserialize;
    reason(Option::<String>::deserialize(d)?).map_err(serde::de::Error::custom)
}
fn owned_reasons<'de, D: serde::Deserializer<'de>>(d: D) -> std::result::Result<Vec<Option<&'static str>>, D::Error> {
    use serde::Deserialize;
    Vec::<Option<String>>::deserialize(d)?.into_iter().map(reason).collect::<std::result::Result<_, _>>()
        .map_err(serde::de::Error::custom)
}

impl Observation {
    pub(crate) fn semantic_bytes(&self) -> Result<Vec<u8>> {
        let mut copy = self.clone();
        copy.capture_nanos = 0;
        bincode::serialize(&copy).map_err(|e| e.to_string())
    }
    pub(crate) fn rebind(&mut self, index: usize, calls: &BTreeMap<usize, usize>) -> Result<()> {
        self.id = index;
        self.capture_nanos = 0; // Cached work must not be reported as executed.
        for write in &mut self.writes {
            for (function, _, _) in &mut write.coverage.calls {
                *function = *calls.get(function).ok_or("unbound frame observation call")?;
            }
        }
        Ok(())
    }
}

fn result_edge(events: &mut Vec<Vec<Event>>, successors: &mut Vec<Vec<usize>>, block: usize,
               target: usize, local: usize, partial: bool, cleanup: Option<usize>) -> usize {
    let edge = events.len();
    let mut event = Event::default();
    event.writes.insert(local);
    if partial { event.reads.insert(local); }
    events.push(vec![event]);
    successors.push(vec![target]);
    // Construct labeled Call outcomes explicitly. The cleanup can reach the
    // same original block without passing through the result write.
    successors[block] = vec![edge];
    if let Some(cleanup) = cleanup { successors[block].push(cleanup); }
    edge
}

pub(crate) fn capture(lower: &mut Lower<'_, '_>) -> Observation {
    let started=std::time::Instant::now();
    let mut observed = Observation {
        id: *lower.exporter.ids.get(&lower.instance).expect("registered instance"),
        name: format!("{}{:?}", lower.tcx().def_path_str(lower.instance.def_id()), lower.instance.args),
        origins: std::mem::take(&mut lower.byte_origins), abi_count: lower.body.arg_count+1, capture_nanos: 0, extent: lower.byte_local_extent,
        slots: lower.locals.clone(), shapes: vec![], reasons: vec![],
        events: vec![], successors: vec![], writes: vec![], baseline: false, decline: None,
    };
    if !lower.byte_origins_complete { observed.decline=Some("origin_bound"); return observed; }
    let count: usize = lower.body.basic_blocks.iter().map(|b| b.statements.len() + 1).sum();
    if lower.locals.is_empty() || lower.locals.len() > MAX_LOCALS || count > MAX_EVENTS {
        observed.decline = Some("input_bound"); return observed;
    }
    let mut old_eligible = vec![];
    for (local, decl) in lower.body.local_decls.iter_enumerated() {
        let ty = lower.mono(decl.ty);
        let layout = lower.layout(ty).expect("previous local layout");
        let size = layout.size.bytes_usize();
        observed.shapes.push((size, layout.align.abi.bytes_usize()));
        let abi = local.as_usize() <= lower.body.arg_count;
        observed.reasons.push(if abi { Some("abi") } else if size == 0 { Some("zero_size") } else { None });
        old_eligible.push(!abi && matches!(ty.kind(), ty::Int(_) | ty::Uint(_) | ty::Float(_) | ty::Bool | ty::Char));
    }
    let span = |bb: usize, event: usize| {
        lower.byte_spans.get(bb).and_then(|b| b.get(event)).copied().flatten()
            .map(|(start, end)| coverage(&lower.code[start..end], lower.registers as usize))
            .unwrap_or_default()
    };
    let mut old_events = vec![];
    let mut normal = vec![];
    for (bb, block) in lower.body.basic_blocks.iter_enumerated() {
        let mut old = vec![];
        let mut events = vec![];
        for (index, statement) in block.statements.iter().enumerate() {
            let location = mir::Location { block: bb, statement_index: index };
            let mut a = Uses { eligible: &mut old_eligible, event: Event::default() };
            a.visit_statement(statement, location); old.push(a.event);
            let mut b = ByteUses { reasons: &mut observed.reasons, event: Event::default() };
            b.visit_statement(statement, location);
            for &local in &b.event.writes {
                observed.writes.push(Write { block: bb.as_usize(), event: index, local, coverage: span(bb.as_usize(), index) });
            }
            events.push(b.event);
        }
        let index = block.statements.len();
        let location = mir::Location { block: bb, statement_index: index };
        let mut a = Uses { eligible: &mut old_eligible, event: Event::default() };
        a.visit_terminator(block.terminator(), location); old.push(a.event);
        let mut b = ByteUses { reasons: &mut observed.reasons, event: Event::default() };
        b.visit_terminator(block.terminator(), location);
        for &local in &b.event.writes {
            observed.writes.push(Write { block: bb.as_usize(), event: index, local, coverage: span(bb.as_usize(), index) });
        }
        if let TerminatorKind::Call { destination, target: Some(target), unwind, .. } = &block.terminator().kind {
            if !destination.projection.iter().any(|p| matches!(p, mir::ProjectionElem::Deref)) {
                normal.push((bb.as_usize(), target.as_usize(), destination.local.as_usize(),
                    !destination.projection.is_empty(), span(bb.as_usize(), index),
                    match unwind { mir::UnwindAction::Cleanup(b) => Some(b.as_usize()), _ => None }));
            }
        }
        events.push(b.event);
        observed.events.push(events); old_events.push(old);
        observed.successors.push(block.terminator().successors().map(|b| b.as_usize()).collect());
    }
    let mut end = 0;
    let uncolored: Vec<_> = observed.shapes.iter().map(|&(n,a)| allocate(&mut end,n,a).unwrap()).collect();
    let baseline = plan(&observed.shapes, old_eligible, old_events, &observed.successors)
        .filter(|(_, size)| *size < end).unwrap_or((uncolored, end));
    assert_eq!(baseline.1, observed.extent, "baseline local extent differs");
    assert!(baseline.0.iter().zip(&observed.slots).all(|(a,b)| a.offset == b.offset && a.size == b.size), "baseline slots differ");
    observed.baseline = true;
    for (block, target, local, partial, coverage, cleanup) in normal {
        let edge = result_edge(&mut observed.events, &mut observed.successors, block, target, local, partial, cleanup);
        observed.writes.push(Write { block: edge, event: 0, local, coverage });
    }
    observed.capture_nanos=started.elapsed().as_nanos();
    observed
}

#[path="aggregate_relocation.rs"]
mod relocation;
pub(crate) fn report(observations: Vec<Observation>, program: &mut Program) {
    relocation::transform(observations,program);
}

#[cfg(test)]
#[path = "byte_writes_tests.rs"]
mod tests;
