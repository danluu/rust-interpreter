//! Owned graph-binding recipes. Resolve against current MIR, never old AllocIds.
use super::*;
use rustc_middle::mir::visit::Visitor;
use serde::{Deserialize, Serialize};
use bincode::Options;

fn allocation_correspondence<K: Eq + std::hash::Hash>(left: &HashMap<K, usize>, right: &HashMap<K, usize>) -> bool {
    // The caller-location hook allocates fresh compiler IDs on every call.
    // Shared IDs must retain their address, and all address alias classes must
    // retain their cardinality. Guest bytes/pointers are compared separately.
    if left.iter().any(|(id, address)| right.get(id).is_some_and(|other| other != address)) { return false; }
    let classes = |map: &HashMap<K, usize>| {
        let mut counts = BTreeMap::new();
        for &address in map.values() { *counts.entry(address).or_insert(0usize) += 1; }
        counts
    };
    classes(left) == classes(right)
}

#[derive(Serialize, Deserialize)]
pub(super) struct Template {
    pub function: Function,
    pub observation: scalar_frame::byte_writes::Observation,
    pub tape: Tape,
}
impl Template {
    pub fn encode(&self) -> Result<Vec<u8>> {
        bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64 * 1024 * 1024)
            .serialize(self).map_err(|e| format!("encode binding template: {e}"))
    }
    pub fn decode(bytes: &[u8]) -> Result<Self> {
        if bytes.len() > 64 * 1024 * 1024 { return Err("binding template exceeds byte bound".into()); }
        bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64 * 1024 * 1024)
            .reject_trailing_bytes().deserialize(bytes).map_err(|e| format!("decode binding template: {e}"))
    }
}

pub(crate) fn enabled() -> Result<bool> {
    match std::env::var_os("RUST_INTERP_BINDING_REPLAY") {
        None => Ok(false),
        Some(value) if value == "0" => Ok(false),
        Some(value) if value == "1" => Ok(true),
        _ => Err("RUST_INTERP_BINDING_REPLAY must be 0 or 1".into()),
    }
}

impl<'tcx> Exporter<'tcx> {
    pub(super) fn replay_seed(&self) -> Self {
        Self {
            tcx: self.tcx, trap_unsupported_calls: self.trap_unsupported_calls,
            run_try_callbacks: self.run_try_callbacks, unavailable_calls: self.unavailable_calls.clone(),
            instances: self.instances.clone(), ids: self.ids.clone(), needs_body: self.needs_body.clone(),
            pending: self.pending.clone(), pointer_shapes: self.pointer_shapes.clone(),
            indirect_shapes: self.indirect_shapes.clone(), allocations: self.allocations.clone(),
            relocation_targets: None, tls_addresses: self.tls_addresses.clone(), runtime_errno: self.runtime_errno,
            binding_replay: false, thread_locals: self.thread_locals.clone(), data: self.data.clone(),
            statics: self.statics.clone(), demand: self.demand, trace: None, trace_parent: None,
            trace_function: None, byte_writes: vec![],
        }
    }
    pub(super) fn verify_replayed_graph(&self, replay: &Self) -> Result<()> {
        macro_rules! compare {
            ($field:ident) => {
                if self.$field != replay.$field {
                    return Err(format!("binding replay exporter {} differs from full lowering", stringify!($field)));
                }
            };
        }
        compare!(instances); compare!(ids); compare!(needs_body); compare!(pending);
        compare!(pointer_shapes); compare!(indirect_shapes);
        if !allocation_correspondence(&self.allocations, &replay.allocations) {
            return Err("binding replay allocation addresses or alias classes differ from full lowering".into());
        }
        compare!(tls_addresses); compare!(runtime_errno); compare!(data); compare!(statics);
        compare!(unavailable_calls);
        if self.thread_locals.len() != replay.thread_locals.len()
            || self.thread_locals.iter().zip(&replay.thread_locals).any(|(a, b)| (a.offset, a.size) != (b.offset, b.size)) {
            return Err("binding replay exporter thread_locals differs from full lowering".into());
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub(super) struct Position { pub block: usize, pub statement: usize }
#[derive(Clone, Debug, Serialize, Deserialize)]
pub(super) enum Source {
    Constant { ordinal: usize, as_scalar: bool },
    FunctionPointer(Position),
    ThreadLocal(Position),
    Caller(Position),
    Errno,
}
#[derive(Clone, Serialize, Deserialize)]
pub(super) enum Event {
    Value { source: Source, register: Reg, original: u128 },
    Call { block: usize, original: usize },
    Indirect(CallShape),
    Unavailable(UnavailableCall),
}
impl Event {
    pub fn kind(&self) -> &'static str {
        match self {
            Self::Value { source, .. } => match source {
                Source::Constant { .. } => "constant", Source::FunctionPointer(_) => "function_pointer",
                Source::ThreadLocal(_) => "thread_local", Source::Caller(_) => "caller", Source::Errno => "errno",
            },
            Self::Call { .. } => "call", Self::Indirect(_) => "indirect", Self::Unavailable(_) => "unavailable",
        }
    }
}
#[derive(Clone, Default, Serialize, Deserialize)]
pub(super) struct Tape {
    pub events: Vec<Event>,
    pub decline: Option<String>,
}
pub(super) struct Recorder {
    constants: HashMap<usize, usize>,
    pub tape: Tape,
}
#[derive(Default)]
struct Constants<'tcx> { values: Vec<mir::ConstOperand<'tcx>>, addresses: Vec<usize> }
impl<'tcx> Visitor<'tcx> for Constants<'tcx> {
    fn visit_const_operand(&mut self, operand: &mir::ConstOperand<'tcx>, _: mir::Location) {
        self.addresses.push(operand as *const _ as usize);
        self.values.push(operand.clone());
    }
}
impl Recorder {
    pub fn new(body: &mir::Body<'_>) -> Self {
        let mut visitor = Constants::default();
        visitor.visit_body(body);
        let constants = visitor.addresses.iter().enumerate().map(|(i, address)| (*address, i)).collect();
        Self { constants, tape: Tape::default() }
    }
    pub fn constant(&mut self, operand: &mir::ConstOperand<'_>, as_scalar: bool) -> Option<Source> {
        match self.constants.get(&(operand as *const _ as usize)).copied() {
            Some(ordinal) => Some(Source::Constant { ordinal, as_scalar }),
            None => { self.decline("constant operand is not owned by the current MIR body"); None }
        }
    }
    pub fn decline(&mut self, reason: &str) {
        self.tape.decline.get_or_insert_with(|| reason.to_owned());
    }
    pub fn record(&mut self, event: Event) {
        if self.tape.events.len() >= 100_000 {
            self.decline("binding event bound");
        } else {
            self.tape.events.push(event);
        }
    }
}

struct Current<'tcx> {
    tcx: TyCtxt<'tcx>, instance: Instance<'tcx>, body: &'tcx mir::Body<'tcx>,
    constants: Option<Constants<'tcx>>,
}
impl<'tcx> Current<'tcx> {
    fn mono<T: TypeFoldable<TyCtxt<'tcx>> + Copy>(&self, value: T) -> T {
        self.instance.instantiate_mir_and_normalize_erasing_regions(
            self.tcx, env(), ty::EarlyBinder::bind(self.tcx, value))
    }
    fn operand_ty(&self, operand: &Operand<'tcx>) -> Ty<'tcx> {
        self.mono(operand.ty(&self.body.local_decls, self.tcx))
    }
    fn block(&self, index: usize) -> Result<&'tcx mir::BasicBlockData<'tcx>> {
        self.body.basic_blocks.raw.get(index).ok_or("binding block out of bounds".into())
    }
    fn rvalue(&self, at: Position) -> Result<&'tcx Rvalue<'tcx>> {
        match &self.block(at.block)?.statements.get(at.statement).ok_or("binding statement out of bounds")?.kind {
            StatementKind::Assign(pair) => Ok(&pair.1),
            _ => Err("binding statement is not an assignment".into()),
        }
    }
    fn call(&self, block: usize) -> Result<Instance<'tcx>> {
        match &self.block(block)?.terminator().kind {
            TerminatorKind::Call { func, .. } => {
                let ty::FnDef(def, args) = *self.operand_ty(func).kind() else {
                    return Err("binding direct call is not FnDef".into());
                };
                let mut instance = Instance::try_resolve(self.tcx, env(), def,
                    self.tcx.instantiate_bound_regions_with_erased(args))
                    .map_err(|e| format!("binding call resolution: {e:?}"))?.ok_or("unresolved binding call")?;
                if let ty::InstanceKind::Intrinsic(def) = instance.def {
                    let intrinsic = self.tcx.intrinsic(def).ok_or("missing binding intrinsic")?;
                    if intrinsic.must_be_overridden { return Err("binding intrinsic needs a shim".into()); }
                    instance.def = ty::InstanceKind::Item(def);
                }
                Ok(instance)
            }
            TerminatorKind::Drop { place, .. } => {
                let ty = self.mono(place.ty(&self.body.local_decls, self.tcx).ty);
                Ok(Instance::resolve_drop_glue(self.tcx, ty))
            }
            _ => Err("binding call source is not a call or drop".into()),
        }
    }
    fn value(&mut self, exporter: &mut Exporter<'tcx>, source: &Source) -> Result<u128> {
        match *source {
            Source::Constant { ordinal, as_scalar } => {
                if self.constants.is_none() {
                    let mut visitor = Constants::default();
                    visitor.visit_body(self.body);
                    self.constants = Some(visitor);
                }
                let operand = self.constants.as_ref().unwrap().values.get(ordinal).ok_or("binding constant ordinal out of bounds")?;
                let cv = self.mono(operand.const_);
                let value = cv.eval(self.tcx, env(), operand.span).map_err(|e| format!("binding constant: {e:?}"))?;
                match value {
                    ConstValue::Scalar(Scalar::Ptr(pointer, _)) => {
                        let base = exporter.alloc(pointer.provenance.alloc_id())?;
                        let bits = base as u128 + pointer.prov_and_relative_offset().1.bytes() as u128;
                        if as_scalar {
                            let size = self.tcx.layout_of(env().as_query_input(cv.ty()))
                                .map_err(|e| format!("binding scalar layout: {e:?}"))?.size.bytes_usize();
                            if size == 0 || size > 16 { return Err("invalid binding scalar size".into()); }
                            Ok(bits & if size == 16 { u128::MAX } else { (1u128 << (size * 8)) - 1 })
                        } else { Ok(bits) }
                    }
                    ConstValue::Indirect { alloc_id, offset } => {
                        Ok(exporter.alloc(alloc_id)?.checked_add(offset.bytes_usize()).ok_or("binding address overflow")? as u128)
                    }
                    ConstValue::Slice { alloc_id, meta } => Ok(exporter.alloc(alloc_id)? as u128 | ((meta as u128) << 64)),
                    _ => Err("binding constant no longer contains a compiler allocation".into()),
                }
            }
            Source::FunctionPointer(at) => {
                let Rvalue::Cast(kind, operand, _) = self.rvalue(at)? else { return Err("binding is not a function cast".into()); };
                let ty = self.operand_ty(operand);
                let instance = match (kind, *ty.kind()) {
                    (CastKind::PointerCoercion(ty::adjustment::PointerCoercion::ReifyFnPointer(_), _), ty::FnDef(def, args)) =>
                        Instance::resolve_for_fn_ptr(self.tcx, env(), def, self.tcx.instantiate_bound_regions_with_erased(args))
                            .ok_or("unresolved binding function pointer")?,
                    (CastKind::PointerCoercion(ty::adjustment::PointerCoercion::ClosureFnPointer(_), _), ty::Closure(def, args)) =>
                        Instance::resolve_closure(self.tcx, def, args, ty::ClosureKind::FnOnce),
                    _ => return Err("binding function cast changed kind".into()),
                };
                Ok(exporter.function_pointer(instance) as u128)
            }
            Source::ThreadLocal(at) => {
                let Rvalue::ThreadLocalRef(def) = self.rvalue(at)? else { return Err("binding is not a TLS reference".into()); };
                Ok(exporter.thread_local(*def)? as u128)
            }
            Source::Caller(at) => {
                let block = self.block(at.block)?;
                if at.statement != block.statements.len() { return Err("caller binding is not a terminator".into()); }
                let term = block.terminator();
                let info = match &term.kind {
                    TerminatorKind::Call { fn_span, .. } => mir::SourceInfo { span: *fn_span, ..term.source_info },
                    TerminatorKind::Drop { .. } => term.source_info,
                    _ => return Err("caller binding is not a call or drop".into()),
                };
                let inherited = self.instance.def.requires_caller_location(self.tcx).then_some(None);
                let span = self.body.caller_location_span(info, inherited, self.tcx, Some)
                    .ok_or("constant caller binding became inherited")?;
                let ConstValue::Scalar(Scalar::Ptr(pointer, _)) = self.tcx.span_as_caller_location(span) else {
                    return Err("binding caller location is not a pointer".into());
                };
                let base = exporter.alloc(pointer.provenance.alloc_id())? as u64;
                Ok(base.checked_add(pointer.prov_and_relative_offset().1.bytes()).ok_or("binding caller overflow")? as u128)
            }
            Source::Errno => Ok(exporter.errno_address()? as u128),
        }
    }
}

#[derive(Default, Serialize)]
pub(super) struct ReplayCosts {
    pub functions: usize,
    instructions: usize,
    immediate_sites: usize,
    events: usize,
    call_sites: usize,
    setup_seconds: f64,
    events_seconds: f64,
    patch_seconds: f64,
}

impl ReplayCosts {
    pub fn phase_seconds(&self) -> f64 {
        self.setup_seconds + self.events_seconds + self.patch_seconds
    }
}

pub(super) fn costs_enabled() -> Result<bool> {
    match std::env::var_os("RUST_INTERP_REPLAY_COSTS") {
        None => Ok(false),
        Some(value) if value == "0" => Ok(false),
        Some(value) if value == "1" => Ok(true),
        _ => Err("RUST_INTERP_REPLAY_COSTS must be 0 or 1".into()),
    }
}

/// Reconstruct owned output and graph effects in the original request order.
/// Every direct function index is a typed Op::Call field, never guessed from bits.
pub(super) fn replay<'tcx>(exporter: &mut Exporter<'tcx>, instance: Instance<'tcx>, index: usize,
    template: Template) -> Result<Function> {
    replay_measured(exporter, instance, index, template, None)
}

/// Coarse optional observation of existing work; no program transformation.
/// These intervals exclude payload decoding and include observer overhead.
pub(super) fn replay_measured<'tcx>(exporter: &mut Exporter<'tcx>, instance: Instance<'tcx>, index: usize,
    template: Template, mut costs: Option<&mut ReplayCosts>) -> Result<Function> {
    let started = costs.as_ref().map(|_| std::time::Instant::now());
    let Template { mut function, observation: mut observed, tape } = template;
    if tape.decline.is_some() { return Err("declined binding tape".into()); }
    let mut current = Current { tcx: exporter.tcx, instance,
        body: exporter.tcx.instance_mir(instance.def), constants: None };
    let mut immediates = HashMap::new();
    for (pc, op) in function.code.iter().enumerate() {
        if let Op::Imm { dst, .. } = op {
            if immediates.insert(*dst, pc).is_some() { return Err("ambiguous binding immediate".into()); }
        }
    }
    if let Some(costs) = costs.as_deref_mut() {
        costs.setup_seconds += started.unwrap().elapsed().as_secs_f64();
        costs.functions += 1;
        costs.instructions += function.code.len();
        costs.immediate_sites += immediates.len();
        costs.events += tape.events.len();
    }
    let events_started = costs.as_ref().map(|_| std::time::Instant::now());
    let mut bound = HashSet::new();
    let mut calls = BTreeMap::new();
    for event in &tape.events {
        match event {
            Event::Value { source, register, original } => {
                if !bound.insert(*register) { return Err("duplicate binding register".into()); }
                let pc = *immediates.get(register).ok_or("missing binding immediate")?;
                let Op::Imm { value, .. } = &mut function.code[pc] else { unreachable!() };
                if value != original { return Err("binding original immediate changed".into()); }
                *value = current.value(exporter, source)?;
            }
            Event::Call { block, original } => {
                let function = exporter.register(current.call(*block)?);
                if calls.insert(*original, function).is_some_and(|previous| previous != function) {
                    return Err("one old call identity resolved to different current instances".into());
                }
            }
            Event::Indirect(shape) => exporter.require_indirect_calls(shape.clone()),
            Event::Unavailable(call) => { exporter.unavailable_calls.insert(call.clone()); }
        }
    }
    if let Some(costs) = costs.as_deref_mut() {
        costs.events_seconds += events_started.unwrap().elapsed().as_secs_f64();
    }
    let patch_started = costs.as_ref().map(|_| std::time::Instant::now());
    let mut call_sites = 0;
    for op in &mut function.code {
        if let Op::Call { function, .. } = op {
            *function = *calls.get(function).ok_or("missing direct call binding")?;
            call_sites += 1;
        }
    }
    observed.rebind(index, &calls)?;
    exporter.byte_writes.push(observed);
    if let Some(costs) = costs {
        costs.patch_seconds += patch_started.unwrap().elapsed().as_secs_f64();
        costs.call_sites += call_sites;
    }
    Ok(function)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn fresh_ids_preserve_alias_classes_and_shared_ids_keep_their_addresses() {
        let original = HashMap::from([(1, 100), (2, 100), (3, 200)]);
        assert!(allocation_correspondence(&original, &HashMap::from([(1, 100), (4, 100), (5, 200)])));
        assert!(!allocation_correspondence(&original, &HashMap::from([(1, 100), (4, 200)])));
        assert!(!allocation_correspondence(&original, &HashMap::from([(1, 200), (4, 100), (5, 100)])));
        assert!(!allocation_correspondence(&original, &HashMap::from([(1, 100), (4, 200), (5, 200)])));
    }
}
