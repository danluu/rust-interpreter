//! Lower checked, concrete MIR into owned instructions with fixed frame offsets.
//! Only rustc's frontend and layout/constant APIs are used here. There is no
//! LLVM/Cranelift execution fallback and no reuse of rustc's runtime interpreter.
use rust_interp_bytecode::{Binary, Function, Op, Program, Reg, Slot, Unary, VERSION};
use rustc_abi::{ExternAbi, TagEncoding, VariantIdx, Variants};
use rustc_hir::def::DefKind;
use rustc_middle::mir::interpret::{AllocId, ConstAllocation, GlobalAlloc, Scalar};
use rustc_middle::mir::{
    self, AggregateKind, BinOp, CastKind, ConstValue, Operand, Place, ProjectionElem, Rvalue,
    StatementKind, TerminatorKind, UnOp,
};
use rustc_middle::ty::layout::{LayoutCx, TyAndLayout};
use rustc_middle::ty::{self, Instance, Ty, TyCtxt, TypeFoldable};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet, VecDeque};

type Result<T> = std::result::Result<T, String>;
mod simd;
mod scalar_frame;
mod scalar_promote;
mod dynamic;
mod float;
mod atomic;
mod entry;
mod caller;
mod system;
mod c_allocator;
mod tls;
mod reachability;
mod allocation;
fn env<'tcx>() -> ty::TypingEnv<'tcx> {
    ty::TypingEnv::fully_monomorphized()
}

fn panic_function(tcx: TyCtxt<'_>, def: rustc_hir::def_id::DefId) -> Option<String> {
    if !matches!(tcx.def_kind(def), DefKind::Fn | DefKind::AssocFn) {
        return None;
    }
    let core = tcx.lang_items().panic_fmt().map(|id| id.krate);
    let std = tcx.lang_items().panic_impl().map(|id| id.krate);
    let alloc = tcx.lang_items().owned_box().map(|id| id.krate);
    // The pinned installed sysroot omits this non-generic MIR. Its entire
    // body is panic!("Arc counter overflow"); keep the panic-as-trap contract.
    let arc_overflow = Some(def.krate) == alloc
        && tcx.def_path_str(def) == "alloc::sync::panic_arc_overflow";
    if Some(def.krate) != core && Some(def.krate) != std && !arc_overflow {
        return None;
    }
    if !tcx
        .fn_sig(def)
        .instantiate_identity()
        .skip_binder()
        .output()
        .is_never()
    {
        return None;
    }
    let name = tcx.def_path_str(def);
    // Installed std omits this non-generic MIR; the pinned body is only a
    // panic reporting LocalKey access after destruction.
    let tls_access_panic = Some(def.krate) == std
        && name == "std::thread::local::panic_access_error";
    // These pinned-core helpers contain only panic!, but the installed
    // metadata omits their non-generic MIR. Preserve the same panic-as-trap
    // contract as core::panicking, including strict integer operations.
    let integer_panic = Some(def.krate) == core
        && (name == "core::num::imp::int_log10::panic_for_nonpositive_argument"
        || name.strip_prefix("core::num::imp::overflow_panic::").is_some_and(|name| {
            matches!(name, "add" | "sub" | "mul" | "rem" | "neg" | "shr" | "shl" | "pow" | "cast_integer")
        }));
    if tcx.lang_items().panic_fmt() == Some(def)
        || tls_access_panic
        || arc_overflow
        || integer_panic
        || name.starts_with("core::panicking::")
        || name.starts_with("std::panicking::")
        || [
            "core::option::expect_failed",
            "std::option::expect_failed",
            "core::option::unwrap_failed",
            "std::option::unwrap_failed",
            "core::result::unwrap_failed",
            "std::result::unwrap_failed",
            "core::slice::index::slice_index_fail",
            "std::slice::index::slice_index_fail",
            "core::str::slice_error_fail",
            "std::str::slice_error_fail",
        ]
        .contains(&name.as_str())
    {
        Some(name)
    } else {
        None
    }
}

// These assignments prepare arguments that our panic-as-trap runtime never
// consumes. They cannot call functions, drop values, or write through a place.
// Calls evaluating message arguments remain in preceding MIR blocks and run.
fn panic_preparation(statement: &mir::Statement<'_>) -> bool {
    match &statement.kind {
        StatementKind::Assign(pair) => {
            pair.0.projection.is_empty()
                && matches!(
                    pair.1,
                    Rvalue::Use(..)
                        | Rvalue::Ref(..)
                        | Rvalue::RawPtr(..)
                        | Rvalue::Cast(..)
                        | Rvalue::Aggregate(..)
                )
        }
        StatementKind::StorageLive(_)
        | StatementKind::StorageDead(_)
        | StatementKind::Nop
        | StatementKind::PlaceMention(..)
        | StatementKind::AscribeUserType(..)
        | StatementKind::FakeRead(..)
        | StatementKind::Coverage(..) => true,
        _ => false,
    }
}

/// Unavailable direct calls retained only by the explicit reachability option.
/// Sorted symbol/caller pairs make diagnostics independent of hash iteration.
#[derive(PartialEq, Eq, PartialOrd, Ord)]
enum UnavailableCallKind { Foreign, Intrinsic }
impl UnavailableCallKind {
    fn name(&self) -> &'static str {
        match self { Self::Foreign => "foreign", Self::Intrinsic => "intrinsic" }
    }
}
#[derive(PartialEq, Eq, PartialOrd, Ord)]
pub struct UnavailableCall {
    kind: UnavailableCallKind,
    name: String,
    caller: String,
}
impl UnavailableCall {
    fn message(&self) -> String {
        format!("unavailable {} call: {:?} in {}", self.kind.name(), self.name, self.caller)
    }
    fn json(&self) -> serde_json::Value {
        serde_json::json!({"kind":self.kind.name(),"name":self.name,"caller":self.caller,"trap_message":self.message()})
    }
}

pub struct Exported {
    pub program: Program,
    unavailable_calls: BTreeSet<UnavailableCall>,
    pub(crate) allocation_trace: Option<crate::allocation_trace::Trace>,
}
impl Exported {
    pub fn unavailable_calls(&self) -> Vec<serde_json::Value> {
        self.unavailable_calls.iter().map(UnavailableCall::json).collect()
    }
}

pub fn export(tcx: TyCtxt<'_>, requested: &[String], demand: bool, test_body: bool,
              inline_leaves: bool, trap_unsupported_calls: bool, run_try_callbacks: bool,
              allocation_trace: bool) -> Result<Exported> {
    if allocation_trace && demand {
        return Err("allocation tracing requires ordinary strict frontend checking".into());
    }
    if tcx.data_layout.pointer_size().bits() != 64
        || tcx.data_layout.endian != rustc_abi::Endian::Little
    {
        return Err("the prototype requires a little-endian 64-bit target".into());
    }
    if requested.is_empty() || requested.len() > 256 {
        return Err("select between 1 and 256 entries".into());
    }
    let mut selected = Vec::new();
    let mut test_results = Vec::new();
    for entry in requested {
        let entries: Vec<_> = tcx
            .hir_body_owners()
            .filter(|id| {
                matches!(tcx.def_kind(*id), DefKind::Fn | DefKind::AssocFn)
                    && (tcx.def_path_str(id.to_def_id()) == *entry
                        || tcx.item_name(id.to_def_id()).as_str() == entry.as_str())
            })
            .collect();
        if entries.len() != 1 {
            return Err(format!(
                "entry {entry:?} matched {} functions; use its full definition path",
                entries.len()
            ));
        }
        let id = entries[0].to_def_id();
        if tcx.generics_of(id).count() != 0 {
            return Err("entry must have concrete, non-generic arguments".into());
        }
        let signature = tcx.normalize_erasing_regions(env(), tcx.fn_sig(id).instantiate_identity());
        let signature = tcx.instantiate_bound_regions_with_erased(signature);
        let output = signature.output();
        let test_result = test_body && matches!(output.kind(), ty::Adt(def, args)
            if tcx.is_diagnostic_item(rustc_span::sym::Result, def.did()) && args.type_at(0).is_unit());
        if test_result && !signature.inputs().is_empty() {
            return Err("Result test entries must have no arguments".into());
        }
        if selected.contains(&id) {
            return Err(format!("entry {entry:?} selects a function more than once"));
        }
        if requested.len() > 1 && (!signature.inputs().is_empty() || (!output.is_unit() && !test_result))
        {
            return Err("batch entries must have no arguments and return unit or Result<(), E>".into());
        }
        if signature
            .inputs()
            .iter()
            .any(|t| !matches!(t.kind(), ty::Int(_) | ty::Uint(_)))
        {
            return Err(
                "CLI entry arguments must be integers; use a typed Rust adapter for other inputs"
                    .into(),
            );
        }
        if !matches!(
            output.kind(),
            ty::Int(_) | ty::Uint(_) | ty::Bool | ty::Char
        ) && !output.is_unit() && !test_result
        {
            return Err("CLI entry result must be an integer, bool, char, or unit".into());
        }
        selected.push(id);
        test_results.push(test_result.then_some(output));
    }
    let mut exporter = Exporter {
        tcx,
        instances: vec![],
        ids: HashMap::new(),
        needs_body: vec![],
        pending: VecDeque::new(),
        pointer_shapes: BTreeMap::new(),
        indirect_shapes: HashSet::new(),
        allocations: HashMap::new(),
        tls_addresses: HashMap::new(),
        runtime_errno: None,
        thread_locals: vec![],
        data: vec![0; 16],
        statics: vec![],
        demand,
        trap_unsupported_calls,
        run_try_callbacks,
        unavailable_calls: BTreeSet::new(),
        trace: allocation_trace.then(crate::allocation_trace::Trace::new),
        trace_parent: None,
        trace_function: None,
        byte_writes: vec![],
    };
    exporter.trace_event(|_| serde_json::json!({"kind": "allocation-trace", "schema_version": 1,
        "target": tcx.sess.opts.target_triple.to_string(), "strict_frontend": !demand,
        "compiler_allocation_ids": "session-local, not stable cache keys",
        "function_indices": "lowering graph before bytecode optimization",
        "max_events": crate::allocation_trace::MAX_EVENTS,
        "max_bytes": crate::allocation_trace::MAX_BYTES,
        "max_allocation_bytes": crate::allocation_trace::MAX_ALLOCATION_BYTES}))?;
    let mut entry_ids = Vec::new();
    for id in selected {
        let mut instance = Instance::mono(tcx, id);
        if instance.def.requires_caller_location(tcx) {
            // A direct CLI entry has no Rust caller frame. Use rustc's normal
            // function-pointer reification shim, which supplies the function's
            // definition location and preserves the visible argument ABI.
            instance = Instance::resolve_for_fn_ptr(tcx, env(), id, instance.args)
                .ok_or("cannot adapt tracked entry")?;
        }
        entry_ids.push(exporter.register(instance));
    }
    let mut functions: Vec<Option<Function>> = vec![];
    while let Some(index) = exporter.pending.pop_front() {
        if exporter.instances.len() >= 10_000 {
            return Err("function expansion limit reached".into());
        }
        let instance = exporter.instances[index];
        let name = tcx.def_path_str(instance.def_id());
        exporter.trace_function = Some(index);
        exporter.trace_event(|tcx| serde_json::json!({"kind": "function", "index": index,
            "definition": tcx.def_path_str(instance.def_id()),
            "instance_kind": format!("{:?}", instance.def),
            "generic_arguments": format!("{:?}", instance.args)}))?;
        let f = Lower::new(&mut exporter, instance)
            .and_then(|lower| lower.lower())
            .map_err(|e| format!("{name}: {e}"))?;
        if exporter.instances.len() > 10_000 {
            return Err("function expansion limit reached".into());
        }
        functions.resize_with(exporter.instances.len(), || None);
        functions[index] = Some(f);
    }
    // Preserve identities without expanding callbacks that cannot match any
    // indirect call's argument/return layout. Unknown shim shapes are always
    // included once an indirect call exists. This is conservative with respect
    // to the same layout checks the VM makes before dispatching a pointer.
    let mut functions: Vec<Function> = exporter
        .instances
        .iter()
        .enumerate()
        .map(|(i, instance)| {
            functions
                .get_mut(i)
                .and_then(Option::take)
                .unwrap_or_else(|| Function {
                    name: format!("{}{:?}", tcx.def_path_str(instance.def_id()), instance.args),
                    frame_size: 0,
                    frame_align: 16,
                    registers: 0,
                    args: vec![],
                    result: Slot { offset: 0, size: 0 },
                    code: vec![Op::Trap {
                        message: "function address has no callable body in this program".into(),
                    }],
                })
        })
        .collect();
    for (entry, output) in entry_ids.iter_mut().zip(test_results) {
        if let Some(output) = output {
            let instance = exporter.instances[*entry];
            exporter.trace_function = Some(*entry);
            let adapter = Lower::test_adapter(&mut exporter, instance, *entry, output)?;
            *entry = functions.len();
            functions.push(adapter);
        }
    }
    let entry = if entry_ids.len() == 1 {
        entry_ids[0]
    } else {
        // One machine, with a shared lowered call graph. Each selected test is
        // an ordinary zero-argument, unit-returning guest call. A panic still
        // stops this experimental runner at the first failing test.
        let entry = functions.len();
        let mut code = vec![Op::Local { dst: 0, offset: 0 }];
        for function in entry_ids {
            code.push(Op::ResetThreadLocals);
            code.push(Op::Call {
                function,
                args: vec![],
                destination: 0,
            });
        }
        code.push(Op::Return);
        functions.push(Function {
            name: format!("selected test batch: {}", requested.join(", ")),
            frame_size: 0,
            frame_align: 16,
            registers: 1,
            args: vec![],
            result: Slot { offset: 0, size: 0 },
            code,
        });
        entry
    };
    if functions[entry].args.iter().any(|s| s.size > 16) || functions[entry].result.size > 16 {
        return Err("CLI entry arguments/result must each fit in 128 bits".into());
    }
    for function in &mut functions {
        rust_interp_bytecode::remove_fallthrough_jumps(&mut function.code)?;
    }
    tcx.dcx().abort_if_errors();
    let mut program = Program {
        version: VERSION
            | if demand {
                rust_interp_bytecode::PARTIAL_VALIDATION
            } else {
                0
            },
        target: tcx.sess.opts.target_triple.to_string(),
        entry,
        functions,
        data: exporter.data,
        statics: exporter.statics,
        thread_locals: exporter.thread_locals,
    };
    scalar_frame::byte_writes::report(exporter.byte_writes, &mut program);
    scalar_frame::report();
    scalar_promote::report();
    let (mut program, calls) = rust_interp_bytecode::optimize_calls(
        program, inline_leaves.then(Default::default))?;
    if let Some(report) = &calls.inlining {
        eprintln!("rust-interp-inline: sites={} operations={} seconds={:.6}",
            report["selected_sites"], report["new_operations"], calls.inline_time.as_secs_f64());
    }
    for (stage, forwarding) in [
        ("before-inline", calls.forwarding_before_inline.as_ref()),
        ("final", Some(&calls.final_forwarding)),
    ] {
        if let Some(forwarding) = forwarding.filter(|r| r.retargeted_calls != 0) {
            eprintln!("rust-interp-forwarding: wrappers={} calls={} longest_chain={} stage={stage}",
                forwarding.wrappers, forwarding.retargeted_calls, forwarding.longest_chain);
        }
    }
    let started = std::time::Instant::now();
    let cfg = rust_interp_bytecode::optimize_control_flow(&mut program)?;
    eprintln!("rust-interp-cfg: before={} after={} seconds={:.6}",
        cfg.old_operations, cfg.new_operations, started.elapsed().as_secs_f64());
    Ok(Exported { program, unavailable_calls: exporter.unavailable_calls,
        allocation_trace: exporter.trace })
}

#[derive(Clone, PartialEq, Eq, Hash)]
struct CallShape {
    args: Vec<usize>,
    result: usize,
}

struct Exporter<'tcx> {
    tcx: TyCtxt<'tcx>,
    trap_unsupported_calls: bool,
    run_try_callbacks: bool,
    unavailable_calls: BTreeSet<UnavailableCall>,
    instances: Vec<Instance<'tcx>>,
    ids: HashMap<Instance<'tcx>, usize>,
    needs_body: Vec<bool>,
    pending: VecDeque<usize>,
    // Scheduling address-taken bodies discovers further functions and data.
    // Iterate in assigned function-ID order so their IDs and offsets remain
    // reproducible across compiler processes.
    pointer_shapes: BTreeMap<usize, Option<CallShape>>,
    indirect_shapes: HashSet<CallShape>,
    allocations: HashMap<AllocId, usize>,
    tls_addresses: HashMap<rustc_hir::def_id::DefId, usize>,
    runtime_errno: Option<usize>,
    thread_locals: Vec<Slot>,
    data: Vec<u8>,
    statics: Vec<u8>,
    demand: bool,
    trace: Option<crate::allocation_trace::Trace>,
    trace_parent: Option<usize>,
    trace_function: Option<usize>,
    byte_writes: Vec<scalar_frame::byte_writes::Observation>,
}
impl<'tcx> Exporter<'tcx> {
    fn register(&mut self, instance: Instance<'tcx>) -> usize {
        self.register_instance(instance, true)
    }
    fn register_instance(&mut self, instance: Instance<'tcx>, needs_body: bool) -> usize {
        if let Some(id) = self.ids.get(&instance) {
            if needs_body && !self.needs_body[*id] {
                self.pending.push_back(*id);
            }
            self.needs_body[*id] |= needs_body;
            return *id;
        }
        let id = self.instances.len();
        self.instances.push(instance);
        self.needs_body.push(needs_body);
        if needs_body {
            self.pending.push_back(id);
        }
        self.ids.insert(instance, id);
        id
    }
    fn function_pointer(&mut self, instance: Instance<'tcx>) -> u64 {
        let shape = self.pointer_shape(instance);
        let required = !self.indirect_shapes.is_empty()
            && shape
                .as_ref()
                .is_none_or(|s| self.indirect_shapes.contains(s));
        let id = self.register_instance(instance, required);
        self.pointer_shapes.insert(id, shape);
        rust_interp_bytecode::FUNCTION_POINTER_TAG | (id as u64 + 1)
    }
    fn pointer_shape(&self, instance: Instance<'tcx>) -> Option<CallShape> {
        if !matches!(instance.def, ty::InstanceKind::Item(_))
            || !matches!(self.tcx.def_kind(instance.def_id()), DefKind::Fn | DefKind::AssocFn)
        {
            // A closure can have InstanceKind::Item but has no fn_sig query.
            // Retain its body conservatively, like other unknown shim layouts;
            // the VM checks the concrete argument/result slots at dispatch.
            return None;
        }
        let sig = self
            .tcx
            .fn_sig(instance.def_id())
            .instantiate(self.tcx, instance.args);
        let sig = self.tcx.normalize_erasing_regions(env(), sig);
        let sig = self.tcx.instantiate_bound_regions_with_erased(sig);
        let mut inputs = sig.inputs().to_vec();
        if sig.abi() == ExternAbi::RustCall {
            let ty::Tuple(fields) = inputs.pop()?.kind() else {
                return None;
            };
            inputs.extend(fields.iter());
        }
        let size = |ty| {
            self.tcx
                .layout_of(env().as_query_input(ty))
                .ok()
                .map(|l| l.size.bytes_usize())
        };
        let mut args = inputs
                .iter()
                .map(|&t| size(t))
                .collect::<Option<Vec<_>>>()?;
        // Match call_arguments and the exported callee slots. Rust closure
        // function pointers rely on omitting the zero-byte FnOnce environment.
        args.retain(|&size| size != 0);
        if instance.def.requires_caller_location(self.tcx) { args.push(8); }
        Some(CallShape {
            args,
            result: size(sig.output())?,
        })
    }
    fn require_indirect_calls(&mut self, shape: CallShape) {
        if !self.indirect_shapes.insert(shape.clone()) {
            return;
        }
        for (&id, candidate) in &self.pointer_shapes {
            if !self.needs_body[id] && candidate.as_ref().is_none_or(|s| *s == shape) {
                self.pending.push_back(id);
                self.needs_body[id] = true;
            }
        }
    }
    fn alloc(&mut self, id: AllocId) -> Result<usize> {
        if self.trace.is_none() {
            return self.alloc_inner(id);
        }
        let cached = self.allocations.get(&id).copied();
        let request = self.trace_event(|_| serde_json::json!({"kind": "allocation-request",
            "allocation_id": id.0.get().to_string(), "cache_hit": cached.is_some(),
            "cached_pointer": cached}))?;
        let result = self.with_trace_parent(request, |this| this.alloc_inner(id))?;
        self.trace_event(|_| serde_json::json!({"kind": "allocation-resolved", "parent": request,
            "allocation_id": id.0.get().to_string(), "pointer": result}))?;
        Ok(result)
    }
    fn alloc_inner(&mut self, id: AllocId) -> Result<usize> {
        if let Some(offset) = self.allocations.get(&id) {
            return Ok(*offset);
        }
        let alloc = match self.tcx.global_alloc(id) {
            GlobalAlloc::Memory(a) => {
                self.trace_event(|_| serde_json::json!({"kind": "allocation-kind", "allocation_kind": "memory"}))?;
                a
            }
            GlobalAlloc::Function { instance } => {
                self.trace_event(|tcx| serde_json::json!({"kind": "allocation-kind", "allocation_kind": "function",
                    "definition": tcx.def_path_str(instance.def_id()),
                    "instance_kind": format!("{:?}", instance.def), "generic_arguments": format!("{:?}", instance.args)}))?;
                let pointer = self.function_pointer(instance) as usize;
                self.allocations.insert(id, pointer);
                return Ok(pointer);
            }
            GlobalAlloc::VTable(ty,predicates) => {
                self.trace_event(|_| serde_json::json!({"kind": "allocation-kind", "allocation_kind": "vtable",
                    "type": format!("{ty:?}"), "predicates": format!("{predicates:?}")}))?;
                let pointer=self.vtable(ty,predicates.principal())?;
                self.allocations.insert(id,pointer);
                return Ok(pointer);
            }
            GlobalAlloc::Static(def) => {
                self.trace_event(|tcx| serde_json::json!({"kind": "allocation-kind", "allocation_kind": "static",
                    "definition": tcx.def_path_str(def), "definition_id": format!("{def:?}")}))?;
                if self.tcx.is_thread_local_static(def) || self.tcx.is_foreign_item(def) {
                    return Err(format!("thread-local or foreign static unsupported: {}", self.tcx.def_path_str(def)));
                }
                self.tcx.eval_static_initializer(def)
                    .map_err(|e| format!("static initializer: {e:?}"))?
            }
            GlobalAlloc::TypeId { ty } => {
                self.trace_event(|_| serde_json::json!({"kind": "allocation-kind", "allocation_kind": "type-id",
                    "type": format!("{ty:?}")}))?;
                // These provenances decorate the numeric pieces of a TypeId.
                // Each relative offset already contains its compiler-provided
                // hash bits; no guest allocation or address rebasing is needed.
                self.allocations.insert(id, 0);
                return Ok(0);
            }
        };
        self.materialize(alloc, Some(id), None)
    }
    fn thread_local(&mut self, def: rustc_hir::def_id::DefId) -> Result<usize> {
        if self.trace.is_none() {
            return self.thread_local_inner(def);
        }
        let cached = self.tls_addresses.get(&def).copied();
        let request = self.trace_event(|tcx| serde_json::json!({"kind": "tls-request",
            "definition": tcx.def_path_str(def), "definition_id": format!("{def:?}"),
            "cache_hit": cached.is_some(), "cached_pointer": cached}))?;
        let pointer = self.with_trace_parent(request, |this| this.thread_local_inner(def))?;
        self.trace_event(|_| serde_json::json!({"kind": "tls-resolved", "parent": request, "pointer": pointer}))?;
        Ok(pointer)
    }
    fn thread_local_inner(&mut self, def: rustc_hir::def_id::DefId) -> Result<usize> {
        if let Some(&address) = self.tls_addresses.get(&def) { return Ok(address); }
        if !self.tcx.is_thread_local_static(def) || self.tcx.is_foreign_item(def) {
            return Err("foreign or invalid thread-local static".into());
        }
        let alloc = self.tcx.eval_static_initializer(def)
            .map_err(|e| format!("thread-local initializer: {e:?}"))?;
        self.materialize(alloc, None, Some(def))
    }
    fn materialize(&mut self, alloc: ConstAllocation<'tcx>, id: Option<AllocId>, tls: Option<rustc_hir::def_id::DefId>) -> Result<usize> {
        let a = alloc.inner();
        // rustc marks both static mut and UnsafeCell-containing initializers
        // mutable, including anonymous allocations reached by their pointers.
        // Reserve them outside allocator-owned ranges, before the guest starts.
        let writable = a.mutability.is_mut();
        let align = (a.align.bytes() as usize).max(16);
        if align > rust_interp_bytecode::MAX_ALIGNMENT {
            return Err("constant alignment exceeds the engine limit".into());
        }
        let length = if writable { self.statics.len() } else { self.data.len() };
        let offset = (length.max(16) + align - 1) & !(align - 1);
        let pointer = offset + if writable { rust_interp_bytecode::HEAP_POINTER_TAG as usize } else { 0 };
        let materialization = self.trace_materialization(alloc, id, tls, pointer, align)?;
        let bytes = if writable { &mut self.statics } else { &mut self.data };
        bytes.resize(offset, 0);
        bytes
            .extend_from_slice(a.inspect_with_uninit_and_ptr_outside_interpreter(0..a.len()));
        if let Some(id) = id { self.allocations.insert(id, pointer); }
        if let Some(def) = tls {
            self.tls_addresses.insert(def, pointer);
            if writable && a.len() != 0 {
                self.thread_locals.push(Slot { offset, size: a.len() });
            }
        }
        for &(at, provenance) in a.provenance().ptrs().iter() {
            let address = offset + at.bytes_usize();
            let bytes = if writable { &self.statics } else { &self.data };
            let original = u64::from_le_bytes(
                bytes[address..address + 8]
                    .try_into()
                    .map_err(|_| "constant pointer")?,
            );
            let edge = self.trace_event(|_| serde_json::json!({"kind": "relocation", "parent": materialization,
                "byte_offset": at.bytes(), "relative_value": original,
                "target_allocation_id": provenance.alloc_id().0.get().to_string()}))?;
            let base = self.with_trace_parent(edge, |this| this.alloc(provenance.alloc_id()))?;
            // Relocations store a target-width relative pointer offset. Rust
            // permits wrapping pointer values outside their allocation; guest
            // accesses still go through the VM's ordinary memory checks.
            let rebased = original.wrapping_add(base as u64);
            let bytes = if writable { &mut self.statics } else { &mut self.data };
            bytes[address..address + 8].copy_from_slice(&rebased.to_le_bytes());
        }
        Ok(pointer)
    }
}

struct Lower<'a, 'tcx> {
    exporter: &'a mut Exporter<'tcx>,
    instance: Instance<'tcx>,
    body: &'tcx mir::Body<'tcx>,
    locals: Vec<Slot>,
    frame_size: usize,
    frame_align: usize,
    registers: u32,
    code: Vec<Op>,
    blocks: Vec<usize>,
    fixups: Vec<usize>,
    caller_location: Option<Slot>,
    byte_local_extent: usize,
    byte_origins: BTreeMap<Reg,usize>,
    byte_origins_complete: bool,
    byte_spans: Vec<Vec<Option<(usize, usize)>>>,
}
#[derive(Clone, Copy)]
struct Location<'tcx> {
    address: Reg,
    ty: Ty<'tcx>,
    variant: Option<VariantIdx>,
    metadata: Option<Reg>,
}

impl<'a, 'tcx> Lower<'a, 'tcx> {
    fn trap_unavailable_call(&mut self, kind: UnavailableCallKind, name: String) {
        let unavailable = UnavailableCall {
            kind, name,
            caller: format!("{}{:?}", self.tcx().def_path_str(self.instance.def_id()), self.instance.args),
        };
        self.code.push(Op::Trap { message: unavailable.message() });
        self.exporter.unavailable_calls.insert(unavailable);
    }

    fn new(exporter: &'a mut Exporter<'tcx>, instance: Instance<'tcx>) -> Result<Self> {
        if matches!(
            instance.def,
            ty::InstanceKind::Intrinsic(..)
                | ty::InstanceKind::LlvmIntrinsic(..)
                | ty::InstanceKind::Virtual(..)
        ) {
            return Err(format!(
                "unsupported callable instance: {:?}, {}",
                instance.def,
                exporter.tcx.def_path_str(instance.def_id())
            ));
        }
        if exporter.demand
            && let Some(local) = instance.def_id().as_local()
        {
            let owner = exporter
                .tcx
                .typeck_root_def_id(local.to_def_id())
                .expect_local();
            exporter.tcx.ensure_ok().check_unsafety(owner);
            exporter.tcx.ensure_ok().mir_borrowck(owner);
            exporter.tcx.ensure_ok().check_transmutes(owner);
            exporter.tcx.dcx().abort_if_errors();
        }
        if !exporter.tcx.is_mir_available(instance.def_id())
            && matches!(instance.def, ty::InstanceKind::Item(_))
            // External constructors encode mir_for_ctfe only. The availability
            // query tests optimized_mir, while instance_mir selects their CTFE
            // body. We lower that body ourselves like other Rust MIR.
            && !matches!(exporter.tcx.def_kind(instance.def_id()), DefKind::Ctor(..))
        {
            return Err(format!(
                "MIR unavailable for {}",
                exporter.tcx.def_path_str(instance.def_id())
            ));
        }
        let body = exporter.tcx.instance_mir(instance.def);
        let mut this = Self::empty(exporter, instance, body);
        for local in body.local_decls.iter() {
            let layout = this.layout(this.mono(local.ty))?;
            if !layout.is_sized() {
                return Err("unsized frame local".into());
            }
            let align = layout.align.abi.bytes() as usize;
            if align > rust_interp_bytecode::MAX_ALIGNMENT {
                return Err("frame alignment exceeds the engine limit".into());
            }
            this.frame_align = this.frame_align.max(align);
            this.frame_size = (this.frame_size + align - 1) & !(align - 1);
            this.locals.push(Slot {
                offset: this.frame_size,
                size: layout.size.bytes_usize(),
            });
            this.frame_size += layout.size.bytes_usize();
        }
        scalar_frame::pack(&mut this)?;
        this.byte_local_extent = this.frame_size;
        if instance.def.requires_caller_location(this.tcx()) {
            this.frame_size = (this.frame_size + 7) & !7;
            this.caller_location = Some(Slot { offset: this.frame_size, size: 8 });
            this.frame_size += 8;
        }
        Ok(this)
    }
    fn empty(exporter: &'a mut Exporter<'tcx>, instance: Instance<'tcx>, body: &'tcx mir::Body<'tcx>) -> Self {
        Self {
            exporter,
            instance,
            body,
            locals: vec![],
            frame_size: 0,
            frame_align: 16,
            registers: 0,
            code: vec![],
            blocks: vec![0; body.basic_blocks.len()],
            fixups: vec![],
            caller_location: None,
            byte_local_extent: 0,
            byte_origins: BTreeMap::new(),
            byte_origins_complete: true,
            byte_spans: if body.local_decls.len() <= 4096 && body.basic_blocks.iter().map(|b| b.statements.len()+1).sum::<usize>() <= 32768 {
                body.basic_blocks.iter().map(|b| vec![None; b.statements.len()+1]).collect()
            } else { vec![] },
        }
    }
    fn tcx(&self) -> TyCtxt<'tcx> {
        self.exporter.tcx
    }
    fn mono<T: TypeFoldable<TyCtxt<'tcx>> + Copy>(&self, value: T) -> T {
        self.instance.instantiate_mir_and_normalize_erasing_regions(
            self.tcx(),
            env(),
            ty::EarlyBinder::bind(self.tcx(), value),
        )
    }
    fn layout(&self, ty: Ty<'tcx>) -> Result<TyAndLayout<'tcx>> {
        self.tcx()
            .layout_of(env().as_query_input(ty))
            .map_err(|e| format!("layout of {ty}: {e:?}"))
    }
    fn field_offset(&self, layout: TyAndLayout<'tcx>, index: usize) -> Result<usize> {
        if index >= layout.fields.count() {
            return Err(format!(
                "field {index} unavailable in layout of {}: {:?}, {:?}",
                layout.ty, layout.fields, layout.variants
            ));
        }
        Ok(layout.fields.offset(index).bytes_usize())
    }
    fn reg(&mut self) -> Reg {
        let r = self.registers;
        self.registers += 1;
        r
    }
    fn imm(&mut self, value: u128) -> Reg {
        let dst = self.reg();
        self.code.push(Op::Imm { dst, value });
        dst
    }
    fn named_local(&mut self, local: mir::Local) -> Reg {
        let dst=self.local(self.locals[local.as_usize()].offset);
        if self.byte_origins.len()<100_000 {
            self.byte_origins.insert(dst,local.as_usize());
        } else { self.byte_origins_complete=false; }
        dst
    }
    fn local(&mut self, offset: usize) -> Reg {
        let dst = self.reg();
        self.code.push(Op::Local { dst, offset });
        dst
    }
    fn load(&mut self, address: Reg, size: usize) -> Result<Reg> {
        if size > 16 {
            return Err(format!("scalar load of {size} bytes"));
        }
        let dst = self.reg();
        self.code.push(Op::Load {
            dst,
            address,
            size: size as u8,
        });
        Ok(dst)
    }
    fn store(&mut self, address: Reg, src: Reg, size: usize) -> Result<()> {
        if size > 16 {
            return Err(format!("scalar store of {size} bytes"));
        }
        self.code.push(Op::Store {
            address,
            src,
            size: size as u8,
        });
        Ok(())
    }
    fn bin(&mut self, op: Binary, a: Reg, b: Reg, bits: u8, signed: bool) -> (Reg, Reg) {
        let dst = self.reg();
        let overflow = self.reg();
        self.code.push(Op::Binary {
            dst,
            overflow,
            op,
            a,
            b,
            bits,
            signed,
        });
        (dst, overflow)
    }
    fn add(&mut self, base: Reg, offset: usize) -> Reg {
        if offset == 0 {
            return base;
        }
        let offset = self.imm(offset as u128);
        self.bin(Binary::Add, base, offset, 64, false).0
    }
    fn temporary(&mut self, size: usize) -> Reg {
        self.temporary_aligned(size, 16)
    }
    fn temporary_aligned(&mut self, size: usize, align: usize) -> Reg {
        self.frame_align = self.frame_align.max(align);
        self.frame_size = self.frame_size.saturating_add(align - 1) & !(align - 1);
        let at = self.frame_size;
        self.frame_size = self.frame_size.saturating_add(size);
        self.local(at)
    }
    fn operand_ty(&self, op: &Operand<'tcx>) -> Ty<'tcx> {
        self.mono(op.ty(&self.body.local_decls, self.tcx()))
    }
    fn place(&mut self, place: Place<'tcx>) -> Result<Location<'tcx>> {
        let mut loc = Location {
            address: self.named_local(place.local),
            ty: self.mono(self.body.local_decls[place.local].ty),
            variant: None,
            metadata: None,
        };
        for projection in place.projection {
            match projection {
                ProjectionElem::Deref => {
                    let pointee = loc
                        .ty
                        .builtin_deref(true)
                        .ok_or("dereference of non-pointer")?;
                    let pointer_size = self.layout(loc.ty)?.size.bytes_usize();
                    loc.metadata = if pointer_size == 16 {
                        let a = self.add(loc.address, 8);
                        Some(self.load(a, 8)?)
                    } else {
                        None
                    };
                    loc.address = self.load(loc.address, 8)?;
                    loc.ty = pointee;
                    loc.variant = None;
                }
                ProjectionElem::Field(index, ty) => {
                    let mut layout = self.layout(loc.ty)?;
                    if let Some(v) = loc.variant {
                        layout = layout.for_variant(&LayoutCx::new(self.tcx(), env()), v);
                    }
                    let field_ty = self.mono(ty);
                    let field_layout = self.layout(field_ty)?;
                    let offset = self.field_offset(layout, index.as_usize())?;
                    if !field_layout.is_sized() && offset != 0
                        && !matches!(field_ty.kind(), ty::Slice(..) | ty::Str)
                    {
                        let (_, align) = self.dynamic_layout(field_ty, loc.metadata)?;
                        let align = self.packed_alignment(loc.ty, align);
                        let offset = self.imm(offset as u128);
                        let offset = self.align_dynamic(offset, align);
                        loc.address = self.bin(Binary::Add, loc.address, offset, 64, false).0;
                    } else {
                        loc.address = self.add(loc.address, offset);
                    }
                    loc.ty = field_ty;
                    loc.variant = None;
                    if self.layout(loc.ty)?.is_sized() {
                        loc.metadata = None;
                    }
                }
                ProjectionElem::Index(index) => {
                    let a = self.named_local(index);
                    let i = self.load(a, 8)?;
                    let elem = loc.ty.builtin_index().ok_or("index of non-array")?;
                    let size = self.imm(self.layout(elem)?.size.bytes() as u128);
                    let offset = self.bin(Binary::Mul, i, size, 64, false).0;
                    loc.address = self.bin(Binary::Add, loc.address, offset, 64, false).0;
                    loc.ty = elem;
                    loc.metadata = None;
                }
                ProjectionElem::ConstantIndex {
                    offset, from_end, ..
                } => {
                    let elem = loc
                        .ty
                        .builtin_index()
                        .ok_or("constant index of non-array")?;
                    let i = if from_end {
                        let len = self.length(loc)?;
                        let off = self.imm(offset as u128);
                        self.bin(Binary::Sub, len, off, 64, false).0
                    } else {
                        self.imm(offset as u128)
                    };
                    let size = self.imm(self.layout(elem)?.size.bytes() as u128);
                    let offset = self.bin(Binary::Mul, i, size, 64, false).0;
                    loc.address = self.bin(Binary::Add, loc.address, offset, 64, false).0;
                    loc.ty = elem;
                    loc.metadata = None;
                }
                ProjectionElem::Subslice { from, to, from_end } => {
                    let elem = loc.ty.builtin_index().ok_or("subslice of non-array")?;
                    loc.address = self.add(
                        loc.address,
                        from as usize * self.layout(elem)?.size.bytes_usize(),
                    );
                    if from_end {
                        let len = self.length(loc)?;
                        let delta = self.imm((from + to) as u128);
                        loc.metadata = Some(self.bin(Binary::Sub, len, delta, 64, false).0);
                        loc.ty = Ty::new_slice(self.tcx(), elem);
                    } else {
                        loc.ty = Ty::new_array(self.tcx(), elem, to - from);
                        loc.metadata = None;
                    }
                }
                ProjectionElem::Downcast(_, variant) => loc.variant = Some(variant),
                ProjectionElem::OpaqueCast(ty) | ProjectionElem::UnwrapUnsafeBinder(ty) => {
                    loc.ty = self.mono(ty)
                }
                other => return Err(format!("unsupported projection {other:?}")),
            }
        }
        Ok(loc)
    }
    fn length(&mut self, loc: Location<'tcx>) -> Result<Reg> {
        if let Some(meta) = loc.metadata {
            return Ok(meta);
        }
        if let ty::Array(_, n) = loc.ty.kind() {
            return Ok(self.imm(n.try_to_target_usize(self.tcx()).ok_or("array length")? as u128));
        }
        Err("slice metadata unavailable".into())
    }
    fn scalar(&mut self, op: &Operand<'tcx>) -> Result<Reg> {
        if let Operand::Constant(c) = op {
            return self.constant_operand(c, true);
        }
        let address = self.operand(op)?;
        self.load(
            address,
            self.layout(self.operand_ty(op))?.size.bytes_usize(),
        )
    }
    fn call_arguments(
        &mut self,
        func: &Operand<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>],
    ) -> Result<(Vec<Reg>, Vec<usize>)> {
        // Evaluate every MIR operand, including ZSTs. Only the transferred
        // argument list omits zero-byte values; MIR still owns all Drop effects.
        let sig = self.operand_ty(func).fn_sig(self.tcx());
        let spread = sig.skip_binder().abi() == ExternAbi::RustCall;
        let mut addresses = Vec::new();
        let mut sizes = Vec::new();
        for (index, arg) in args.iter().enumerate() {
            let ty = self.operand_ty(&arg.node);
            let layout = self.layout(ty)?;
            let address = self.operand(&arg.node)?;
            if spread && index + 1 == args.len() {
                let ty::Tuple(fields) = ty.kind() else {
                    return Err("RustCall's final argument must be a tuple".into());
                };
                for (field, ty) in fields.iter().enumerate() {
                    let size = self.layout(ty)?.size.bytes_usize();
                    if size != 0 {
                        addresses.push(self.add(address, self.field_offset(layout, field)?));
                        sizes.push(size);
                    }
                }
            } else if !layout.is_zst() {
                addresses.push(address);
                sizes.push(layout.size.bytes_usize());
            }
        }
        Ok((addresses, sizes))
    }
    fn operand(&mut self, op: &Operand<'tcx>) -> Result<Reg> {
        match op {
            Operand::Copy(place) | Operand::Move(place) => Ok(self.place(*place)?.address),
            Operand::Constant(c) => self.constant_operand(c, false),
            Operand::RuntimeChecks(checks) => {
                let value = self.imm(checks.value(self.tcx().sess) as u128);
                let address = self.temporary(1);
                self.store(address, value, 1)?;
                Ok(address)
            }
        }
    }
    fn constant_operand(&mut self, c: &mir::ConstOperand<'tcx>, as_scalar: bool) -> Result<Reg> {
        let cv = self.mono(c.const_);
        let size = self.layout(cv.ty())?.size.bytes_usize();
        if size == 0 {
            return Ok(self.imm(0));
        }
        let value = cv
            .eval(self.tcx(), env(), c.span)
            .map_err(|e| format!("constant evaluation: {e:?}"))?;
        let origin = if matches!(&value, ConstValue::Scalar(Scalar::Ptr(..))
            | ConstValue::Indirect { .. } | ConstValue::Slice { .. }) {
            self.exporter.trace_event(|tcx| serde_json::json!({"kind": "constant-origin",
                "operand": format!("{cv:?}"), "evaluated": format!("{value:?}"),
                "source": tcx.sess.source_map().span_to_diagnostic_string(c.span),
                "size": size, "as_scalar": as_scalar}))?
        } else { None };
        let address = match value {
            ConstValue::Scalar(s) => {
                let bits = match s {
                    Scalar::Int(i) => i.to_bits(i.size()),
                    Scalar::Ptr(p, _) => {
                        (self.exporter.with_trace_parent(origin, |e| e.alloc(p.provenance.alloc_id()))? as u128)
                            + p.prov_and_relative_offset().1.bytes() as u128
                    }
                };
                if as_scalar {
                    if size > 16 {
                        return Err(format!("scalar load of {size} bytes"));
                    }
                    // Match the old store/load truncation, including constant
                    // pointers whose relative offset wraps the target width.
                    let mask = if size == 16 { u128::MAX } else { (1u128 << (size * 8)) - 1 };
                    return Ok(self.imm(bits & mask));
                }
                // Calls and other address consumers still receive storage.
                let src = self.imm(bits);
                let address = self.temporary(size);
                self.store(address, src, size)?;
                address
            }
            ConstValue::Indirect { alloc_id, offset } => {
                let at = self.exporter.with_trace_parent(origin, |e| e.alloc(alloc_id))? + offset.bytes_usize();
                self.imm(at as u128)
            }
            ConstValue::Slice { alloc_id, meta } => {
                let at = self.exporter.with_trace_parent(origin, |e| e.alloc(alloc_id))?;
                let bits = (at as u128) | ((meta as u128) << 64);
                let src = self.imm(bits);
                let address = self.temporary(16);
                self.store(address, src, 16)?;
                address
            }
            other => return Err(format!("unsupported constant {other:?}")),
        };
        if as_scalar { self.load(address, size) } else { Ok(address) }
    }
    fn integer(&self, ty: Ty<'tcx>) -> Result<(u8, bool)> {
        match ty.kind() {
            ty::Bool | ty::Char | ty::Uint(_) | ty::Int(_) => Ok((
                self.layout(ty)?.size.bits() as u8,
                matches!(ty.kind(), ty::Int(_)),
            )),
            ty::RawPtr(..) | ty::Ref(..) | ty::FnPtr(..) if self.layout(ty)?.size.bytes() == 8 => {
                Ok((64, false))
            }
            _ => Err(format!("expected integer or thin pointer, got {ty}")),
        }
    }
    fn set_discriminant(&mut self, loc: Location<'tcx>, variant: VariantIdx) -> Result<()> {
        let layout = self.layout(loc.ty)?;
        if let Variants::Multiple {
            tag,
            tag_field,
            ref tag_encoding,
            ..
        } = layout.variants
        {
            let value = match *tag_encoding {
                TagEncoding::Direct => {
                    loc.ty
                        .discriminant_for_variant(self.tcx(), variant)
                        .ok_or("missing discriminant")?
                        .val
                }
                TagEncoding::Niche {
                    untagged_variant,
                    ref niche_variants,
                    niche_start,
                } => {
                    if variant == untagged_variant {
                        return Ok(());
                    }
                    niche_start
                        .wrapping_add((variant.as_u32() - niche_variants.start.as_u32()) as u128)
                }
            };
            let at = self.add(
                loc.address,
                self.field_offset(layout, tag_field.as_usize())?,
            );
            let value = self.imm(value);
            self.store(at, value, tag.size(&self.tcx()).bytes_usize())?;
        }
        Ok(())
    }
    fn discriminant(&mut self, loc: Location<'tcx>, output_bits: u8) -> Result<Reg> {
        let layout = self.layout(loc.ty)?;
        match layout.variants {
            Variants::Single { index } => Ok(self.imm(
                loc.ty
                    .discriminant_for_variant(self.tcx(), index)
                    .map_or(index.as_u32() as u128, |d| d.val),
            )),
            Variants::Multiple {
                tag,
                tag_field,
                ref tag_encoding,
                ..
            } => {
                let at = self.add(
                    loc.address,
                    self.field_offset(layout, tag_field.as_usize())?,
                );
                let size = tag.size(&self.tcx()).bytes_usize();
                let value = self.load(at, size)?;
                match *tag_encoding {
                    TagEncoding::Direct => {
                        let dst = self.reg();
                        self.code.push(Op::Cast {
                            dst,
                            src: value,
                            from: (size * 8) as u8,
                            to: output_bits,
                            signed: matches!(tag.primitive(), rustc_abi::Primitive::Int(_, true)),
                        });
                        Ok(dst)
                    }
                    TagEncoding::Niche {
                        untagged_variant,
                        ref niche_variants,
                        niche_start,
                    } => {
                        let start = self.imm(niche_start);
                        let relative = self
                            .bin(Binary::Sub, value, start, (size * 8) as u8, false)
                            .0;
                        let max = self.imm(
                            (niche_variants.last.as_u32() - niche_variants.start.as_u32()) as u128,
                        );
                        let condition = self
                            .bin(Binary::Le, relative, max, (size * 8) as u8, false)
                            .0;
                        let start_variant = self.imm(niche_variants.start.as_u32() as u128);
                        let tagged = self
                            .bin(Binary::Add, relative, start_variant, output_bits, false)
                            .0;
                        let untagged = self.imm(untagged_variant.as_u32() as u128);
                        let dst = self.reg();
                        self.code.push(Op::Select {
                            dst,
                            condition,
                            yes: tagged,
                            no: untagged,
                        });
                        Ok(dst)
                    }
                }
            }
            Variants::Empty => {
                // Generic MIR can retain impossible branches (for example a
                // Try residual containing Infallible). There is no valid
                // discriminant to read if execution ever reaches this path.
                self.code.push(Op::Trap {
                    message: "read discriminant of uninhabited type".into(),
                });
                Ok(self.imm(0))
            }
        }
    }
    fn assign(&mut self, place: Place<'tcx>, value: &Rvalue<'tcx>) -> Result<()> {
        let dest = self.place(place)?;
        let layout = self.layout(dest.ty)?;
        let size = layout.size.bytes_usize();
        match value {
            Rvalue::ThreadLocalRef(def) => {
                let pointer = self.exporter.thread_local(*def)?;
                let pointer = self.imm(pointer as u128);
                self.store(dest.address, pointer, 8)?;
            }
            Rvalue::Use(op, _) => {
                let src = self.operand(op)?;
                self.code.push(Op::Copy {
                    dst: dest.address,
                    src,
                    size,
                });
            }
            Rvalue::Ref(_, _, p) | Rvalue::RawPtr(_, p) => {
                let loc = self.place(*p)?;
                self.store(dest.address, loc.address, 8)?;
                if size == 16 {
                    let meta = self.length(loc)?;
                    let at = self.add(dest.address, 8);
                    self.store(at, meta, 8)?;
                }
            }
            Rvalue::BinaryOp(op, args) => {
                let (a, b) = (&args.0, &args.1);
                let operand_ty = self.operand_ty(a);
                if matches!(operand_ty.kind(), ty::Float(_)) {
                    return self.float_binary(*op, a, b, dest);
                }
                if matches!(op, BinOp::Eq | BinOp::Ne)
                    && matches!(operand_ty.kind(), ty::RawPtr(..))
                    && self.layout(operand_ty)?.size.bytes() == 16
                {
                    let other_ty = self.operand_ty(b);
                    if !matches!(other_ty.kind(), ty::RawPtr(..))
                        || self.layout(other_ty)?.size.bytes() != 16
                        || !dest.ty.is_bool()
                    {
                        return Err("unsupported wide-pointer equality layout".into());
                    }
                    // Our pointer representation stores address then metadata
                    // as two 64-bit words. MIR pointer equality compares both;
                    // ptr::addr_eq has already erased metadata before this point.
                    // Keep the comparisons separate so both can run in the
                    // native 64-bit emitter. Ordering is deliberately excluded:
                    // a little-endian u128 comparison would order metadata first.
                    let a = self.operand(a)?;
                    let b = self.operand(b)?;
                    let a_address = self.load(a, 8)?;
                    let b_address = self.load(b, 8)?;
                    let a_meta = self.add(a, 8);
                    let b_meta = self.add(b, 8);
                    let a_meta = self.load(a_meta, 8)?;
                    let b_meta = self.load(b_meta, 8)?;
                    let (compare, combine) = if matches!(op, BinOp::Eq) {
                        (Binary::Eq, Binary::And)
                    } else {
                        (Binary::Ne, Binary::Or)
                    };
                    let address = self.bin(compare, a_address, b_address, 64, false).0;
                    let metadata = self.bin(compare, a_meta, b_meta, 64, false).0;
                    let result = self.bin(combine, address, metadata, 8, false).0;
                    return self.store(dest.address, result, size);
                }
                let (bits, signed) = if matches!(op, BinOp::Offset) {
                    (64, false)
                } else {
                    self.integer(operand_ty)?
                };
                let a = self.scalar(a)?;
                let mut b = self.scalar(b)?;
                let binary = match op {
                    BinOp::Add | BinOp::AddUnchecked | BinOp::AddWithOverflow => Binary::Add,
                    BinOp::Sub | BinOp::SubUnchecked | BinOp::SubWithOverflow => Binary::Sub,
                    BinOp::Mul | BinOp::MulUnchecked | BinOp::MulWithOverflow => Binary::Mul,
                    BinOp::Div => Binary::Div,
                    BinOp::Rem => Binary::Rem,
                    BinOp::BitAnd => Binary::And,
                    BinOp::BitOr => Binary::Or,
                    BinOp::BitXor => Binary::Xor,
                    BinOp::Shl | BinOp::ShlUnchecked => Binary::Shl,
                    BinOp::Shr | BinOp::ShrUnchecked => Binary::Shr,
                    BinOp::Eq => Binary::Eq,
                    BinOp::Ne => Binary::Ne,
                    BinOp::Lt => Binary::Lt,
                    BinOp::Le => Binary::Le,
                    BinOp::Gt => Binary::Gt,
                    BinOp::Ge => Binary::Ge,
                    BinOp::Cmp => Binary::Cmp,
                    BinOp::Offset => {
                        let pointee = operand_ty
                            .builtin_deref(true)
                            .ok_or("pointer offset type")?;
                        let scale = self.imm(self.layout(pointee)?.size.bytes() as u128);
                        b = self.bin(Binary::Mul, b, scale, 64, false).0;
                        Binary::Add
                    }
                };
                let (result, overflow) = self.bin(binary, a, b, bits, signed);
                if matches!(
                    op,
                    BinOp::AddWithOverflow | BinOp::SubWithOverflow | BinOp::MulWithOverflow
                ) {
                    let first = self.add(dest.address, self.field_offset(layout, 0)?);
                    let second = self.add(dest.address, self.field_offset(layout, 1)?);
                    self.store(first, result, (bits / 8) as usize)?;
                    self.store(second, overflow, 1)?;
                } else {
                    self.store(dest.address, result, size)?;
                }
            }
            Rvalue::UnaryOp(op, operand) => {
                if matches!(op, UnOp::Neg) && matches!(self.operand_ty(operand).kind(), ty::Float(_)) {
                    return self.float_negate(operand, dest);
                }
                let result = if matches!(op, UnOp::PtrMetadata) {
                    let ptr = self.operand(operand)?;
                    if self.layout(self.operand_ty(operand))?.size.bytes() == 16 {
                        let at = self.add(ptr, 8);
                        self.load(at, 8)?
                    } else {
                        self.imm(0)
                    }
                } else {
                    let ty = self.operand_ty(operand);
                    let (bits, _) = self.integer(ty)?;
                    let src = self.scalar(operand)?;
                    let dst = self.reg();
                    if matches!(ty.kind(), ty::Bool) {
                        let one = self.imm(1);
                        self.bin(Binary::Xor, src, one, 8, false).0
                    } else {
                        self.code.push(Op::Unary {
                            dst,
                            src,
                            bits,
                            op: match op {
                                UnOp::Not => Unary::Not,
                                UnOp::Neg => Unary::Neg,
                                _ => return Err(format!("unary {op:?}")),
                            },
                        });
                        dst
                    }
                };
                self.store(dest.address, result, size)?;
            }
            Rvalue::Cast(kind, operand, _) => {
                let ty = self.operand_ty(operand);
                if matches!(
                    kind,
                    CastKind::PointerCoercion(
                        ty::adjustment::PointerCoercion::ReifyFnPointer(_),
                        _
                    )
                ) {
                    let ty::FnDef(def, args) = *ty.kind() else {
                        return Err("reified pointer source is not a function item".into());
                    };
                    let instance = Instance::resolve_for_fn_ptr(
                        self.tcx(),
                        env(),
                        def,
                        self.tcx().instantiate_bound_regions_with_erased(args),
                    )
                    .ok_or("unresolved function pointer")?;
                    let pointer = self.exporter.function_pointer(instance);
                    let value = self.imm(pointer as u128);
                    self.store(dest.address, value, size)?;
                } else if matches!(
                    kind,
                    CastKind::PointerCoercion(ty::adjustment::PointerCoercion::ClosureFnPointer(_), _)
                ) {
                    let ty::Closure(def, args) = *ty.kind() else {
                        return Err("closure function pointer source is not a closure".into());
                    };
                    if !args.as_closure().upvar_tys().is_empty() || !self.layout(ty)?.is_zst() {
                        return Err("capturing closure cannot become a function pointer".into());
                    }
                    if !matches!(dest.ty.kind(), ty::FnPtr(..)) || size != 8 {
                        return Err("unsupported closure function pointer representation".into());
                    }
                    // Preserve operand evaluation even though its closure
                    // environment occupies no bytes in the call ABI.
                    let _ = self.operand(operand)?;
                    let instance = Instance::resolve_closure(self.tcx(), def, args, ty::ClosureKind::FnOnce);
                    if instance.def.requires_caller_location(self.tcx()) {
                        return Err("tracked closure function pointer requires a reification shim".into());
                    }
                    let pointer = self.exporter.function_pointer(instance);
                    let value = self.imm(pointer as u128);
                    self.store(dest.address, value, size)?;
                } else if matches!(
                    kind,
                    CastKind::PointerCoercion(ty::adjustment::PointerCoercion::Unsize, _)
                ) {
                    self.unsize_pointer(operand,dest)?;
                } else if matches!(kind, CastKind::IntToInt) {
                    let (from, signed) = self.integer(ty)?;
                    let (to, _) = self.integer(dest.ty)?;
                    let src = self.scalar(operand)?;
                    let dst = self.reg();
                    self.code.push(Op::Cast {
                        dst,
                        src,
                        from,
                        to,
                        signed,
                    });
                    self.store(dest.address, dst, size)?;
                } else if matches!(kind, CastKind::IntToFloat | CastKind::FloatToInt | CastKind::FloatToFloat) {
                    self.float_cast(*kind, operand, dest)?;
                } else if matches!(
                    kind,
                    CastKind::Transmute
                        | CastKind::PtrToPtr
                        | CastKind::FnPtrToPtr
                        | CastKind::PointerCoercion(
                            ty::adjustment::PointerCoercion::UnsafeFnPointer,
                            _
                        )
                        | CastKind::Subtype
                        | CastKind::PointerExposeProvenance
                        | CastKind::PointerWithExposedProvenance
                        | CastKind::BoxDerefTransmute
                ) {
                    let source_size = self.layout(ty)?.size.bytes_usize();
                    if source_size != size
                        && !(matches!(kind, CastKind::PtrToPtr) && source_size == 16 && size == 8)
                    {
                        return Err("cast size mismatch".into());
                    }
                    let src = self.operand(operand)?;
                    self.code.push(Op::Copy {
                        dst: dest.address,
                        src,
                        size,
                    });
                } else {
                    return Err(format!("unsupported cast {kind:?}"));
                }
            }
            Rvalue::Aggregate(kind, fields) => {
                if matches!(**kind, AggregateKind::RawPtr(..)) {
                    // MIR includes a metadata operand even for thin pointers,
                    // whose layout is Primitive and has no projectable fields.
                    // Wide pointers retain the target's data/metadata offsets.
                    if fields.len() != 2 {
                        return Err("raw pointer aggregate requires data and metadata".into());
                    }
                    let data = &fields[rustc_abi::FieldIdx::from_usize(0)];
                    let metadata = &fields[rustc_abi::FieldIdx::from_usize(1)];
                    let data_size = self.layout(self.operand_ty(data))?.size.bytes_usize();
                    let metadata_size = self.layout(self.operand_ty(metadata))?.size.bytes_usize();
                    if data_size != 8 || !matches!((size, metadata_size), (8, 0) | (16, 8)) {
                        return Err("unsupported raw pointer aggregate layout".into());
                    }
                    let data_at = if size == 8 { 0 } else { self.field_offset(layout, 0)? };
                    let dst = self.add(dest.address, data_at);
                    let src = self.operand(data)?;
                    self.code.push(Op::Copy { dst, src, size: data_size });
                    if metadata_size != 0 {
                        let offset = self.field_offset(layout, 1)?;
                        let dst = self.add(dest.address, offset);
                        let src = self.operand(metadata)?;
                        self.code.push(Op::Copy { dst, src, size: metadata_size });
                    }
                    return Ok(());
                }
                let mut field_layout = layout;
                if let AggregateKind::Adt(_, variant, _, _, _) = **kind {
                    self.set_discriminant(dest, variant)?;
                    field_layout = layout.for_variant(&LayoutCx::new(self.tcx(), env()), variant);
                }
                for (index, operand) in fields.iter_enumerated() {
                    let offset = self.field_offset(field_layout, index.as_usize())?;
                    let dst = self.add(dest.address, offset);
                    let src = self.operand(operand)?;
                    let size = self.layout(self.operand_ty(operand))?.size.bytes_usize();
                    self.code.push(Op::Copy { dst, src, size });
                }
            }
            Rvalue::Repeat(operand, count) => {
                let count = self
                    .mono(*count)
                    .try_to_target_usize(self.tcx())
                    .ok_or("repeat count")?;
                let elem_size = self.layout(self.operand_ty(operand))?.size.bytes_usize();
                let src = self.operand(operand)?;
                if count > 100_000 {
                    return Err("repeat expansion limit".into());
                }
                for i in 0..count {
                    let dst = self.add(dest.address, i as usize * elem_size);
                    self.code.push(Op::Copy {
                        dst,
                        src,
                        size: elem_size,
                    });
                }
            }
            Rvalue::Discriminant(p) => {
                let loc = self.place(*p)?;
                let value = self.discriminant(loc, (size * 8) as u8)?;
                self.store(dest.address, value, size)?;
            }
            other => return Err(format!("unsupported rvalue {other:?}")),
        }
        Ok(())
    }
    fn jump(&mut self, target: mir::BasicBlock) {
        self.fixups.push(self.code.len());
        self.code.push(Op::Jump {
            target: target.as_usize(),
        });
    }
    fn allocation_function(
        &mut self,
        instance: Instance<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>],
        destination: Place<'tcx>,
    ) -> Result<bool> {
        let Some(global) = self.tcx().lang_items().global_alloc_ty() else {
            return Ok(false);
        };
        let def = instance.def_id();
        if def.krate != global.krate {
            return Ok(false);
        }
        let Some(name) = self.tcx().opt_item_name(def) else {
            return Ok(false);
        };
        let name = name.as_str();
        let reserve_error = ["::raw_vec::handle_error", "::raw_vec::capacity_overflow"]
            .iter()
            .any(|suffix| self.tcx().def_path_str(def).ends_with(suffix));
        if ![
            "__rust_alloc",
            "__rust_alloc_zeroed",
            "__rust_dealloc",
            "__rust_realloc",
            "__rust_no_alloc_shim_is_unstable_v2",
            "handle_alloc_error",
            "__rust_alloc_error_handler",
        ]
        .contains(&name)
            && !reserve_error
        {
            return Ok(false);
        }
        // This runtime implements the standard global allocator contract.
        // A user allocator or error handler may have observable behavior.
        let tcx = self.tcx();
        let standard = tcx
            .lang_items()
            .panic_impl()
            .map(|id| id.krate)
            .filter(|&c| {
                c != rustc_hir::def_id::LOCAL_CRATE && tcx.crate_name(c).as_str() == "std"
            });
        for c in
            std::iter::once(rustc_hir::def_id::LOCAL_CRATE).chain(tcx.crates(()).iter().copied())
        {
            if tcx.has_global_allocator(c) {
                return Err("custom global allocators are not yet supported".into());
            }
            if tcx.has_alloc_error_handler(c) && Some(c) != standard {
                return Err("custom allocation error handlers are not yet supported".into());
            }
        }
        if name == "__rust_no_alloc_shim_is_unstable_v2" {
            return Ok(true);
        }
        if name == "handle_alloc_error" || name == "__rust_alloc_error_handler" || reserve_error {
            self.code.push(Op::Trap {
                message: "guest capacity or allocation error".into(),
            });
            return Ok(true);
        }
        let values = args
            .iter()
            .map(|a| self.scalar(&a.node))
            .collect::<Result<Vec<_>>>()?;
        match name {
            "__rust_alloc" | "__rust_alloc_zeroed" => {
                let dst = self.reg();
                self.code.push(Op::Allocate {
                    dst,
                    size: values[0],
                    align: values[1],
                    zeroed: name == "__rust_alloc_zeroed",
                });
                let destination = self.place(destination)?;
                self.store(destination.address, dst, 8)?;
            }
            "__rust_dealloc" => self.code.push(Op::Deallocate {
                pointer: values[0],
                size: values[1],
                align: values[2],
            }),
            "__rust_realloc" => {
                let dst = self.reg();
                self.code.push(Op::Reallocate {
                    dst,
                    pointer: values[0],
                    old_size: values[1],
                    align: values[2],
                    new_size: values[3],
                });
                let destination = self.place(destination)?;
                self.store(destination.address, dst, 8)?;
            }
            _ => unreachable!(),
        }
        Ok(true)
    }
    fn intrinsic(
        &mut self,
        instance: Instance<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>],
        destination: Place<'tcx>,
        source_info: mir::SourceInfo,
    ) -> Result<bool> {
        if matches!(instance.def, ty::InstanceKind::LlvmIntrinsic(..)) {
            return self.target_intrinsic(instance, args, destination);
        }
        let Some(intrinsic) = self.tcx().intrinsic(instance.def_id()) else {
            return Ok(false);
        };
        let name = intrinsic.name.as_str();
        let dest = self.place(destination)?;
        let size = self.layout(dest.ty)?.size.bytes_usize();
        if name == "catch_unwind" && self.exporter.run_try_callbacks {
            return self.try_callback(args, dest);
        }
        if name == "catch_unwind" && self.exporter.trap_unsupported_calls {
            // This opt-in boundary is not an implementation of unwinding.
            // Preserve argument materialization and stop without inventing the
            // intrinsic's boolean result or invoking either callback.
            if args.len() != 3 || !dest.ty.is_bool() || size != 1 {
                return Err("invalid catch_unwind signature".into());
            }
            for arg in args { let _ = self.operand(&arg.node)?; }
            self.trap_unavailable_call(UnavailableCallKind::Intrinsic, name.to_owned());
            return Ok(true);
        }
        if name == "caller_location" {
            if !args.is_empty() || size != 8 {
                return Err("invalid caller_location signature".into());
            }
            let src = self.caller_argument(source_info)?;
            self.code.push(Op::Copy { dst: dest.address, src, size: 8 });
            return Ok(true);
        }
        if name.starts_with("simd_") {
            return self.simd_intrinsic(name, args, dest);
        }
        if self.float_intrinsic(name, args, dest)? {
            return Ok(true);
        }
        if name.starts_with("atomic_") {
            return self.atomic_intrinsic(instance, name, args, dest);
        }
        let binary = match name {
            "rotate_left" => Some(Binary::RotateLeft),
            "rotate_right" => Some(Binary::RotateRight),
            "wrapping_add" => Some(Binary::Add),
            "wrapping_sub" => Some(Binary::Sub),
            "wrapping_mul" => Some(Binary::Mul),
            "unchecked_add" => Some(Binary::Add),
            "unchecked_sub" => Some(Binary::Sub),
            "unchecked_mul" => Some(Binary::Mul),
            "unchecked_shl" => Some(Binary::Shl),
            "unchecked_shr" => Some(Binary::Shr),
            _ => None,
        };
        if let Some(op) = binary {
            let (bits, signed) = self.integer(self.operand_ty(&args[0].node))?;
            let a = self.scalar(&args[0].node)?;
            let b = self.scalar(&args[1].node)?;
            let value = self.bin(op, a, b, bits, signed).0;
            self.store(dest.address, value, size)?;
            return Ok(true);
        }
        let unary = match name {
            "ctpop" => Some(Unary::CountOnes),
            "ctlz" | "ctlz_nonzero" => Some(Unary::LeadingZeros),
            "cttz" | "cttz_nonzero" => Some(Unary::TrailingZeros),
            "bswap" => Some(Unary::SwapBytes),
            _ => None,
        };
        if let Some(op) = unary {
            let (bits, _) = self.integer(self.operand_ty(&args[0].node))?;
            let src = self.scalar(&args[0].node)?;
            let dst = self.reg();
            self.code.push(Op::Unary { dst, op, src, bits });
            self.store(dest.address, dst, size)?;
            return Ok(true);
        }
        match name {
            "cold_path" => {}
            "arith_offset" | "offset" => {
                let pointer = self.scalar(&args[0].node)?;
                let count = self.scalar(&args[1].node)?;
                let scale = self.imm(self.layout(instance.args.type_at(0))?.size.bytes() as u128);
                let offset = self.bin(Binary::Mul, count, scale, 64, false).0;
                let value = self.bin(Binary::Add, pointer, offset, 64, false).0;
                self.store(dest.address, value, size)?;
            }
            "ptr_offset_from" | "ptr_offset_from_unsigned" => {
                let left = self.scalar(&args[0].node)?;
                let right = self.scalar(&args[1].node)?;
                let unsigned = name == "ptr_offset_from_unsigned";
                if unsigned {
                    let ordered = self.bin(Binary::Ge, left, right, 64, false).0;
                    self.code.push(Op::Assert {
                        value: ordered,
                        expected: true,
                        message: "unsigned pointer difference is negative".into(),
                    });
                }
                let difference = self.bin(Binary::Sub, left, right, 64, false).0;
                let scale = self.imm(self.layout(instance.args.type_at(0))?.size.bytes() as u128);
                let value = self.bin(Binary::Div, difference, scale, 64, !unsigned).0;
                self.store(dest.address, value, size)?;
            }
            "copy" => {
                let src = self.scalar(&args[0].node)?;
                let dst = self.scalar(&args[1].node)?;
                let count = self.scalar(&args[2].node)?;
                let scale = self.imm(self.layout(instance.args.type_at(0))?.size.bytes() as u128);
                let (size, overflow) = self.bin(Binary::Mul, count, scale, 64, false);
                self.code.push(Op::Assert {
                    value: overflow,
                    expected: false,
                    message: "copy size overflow".into(),
                });
                self.code.push(Op::CopyDynamic { dst, src, size });
            }
            "ptr_mask" => {
                // The pinned intrinsic takes a thin pointer. Public .mask()
                // methods preserve any fat-pointer metadata in their Rust MIR.
                if args.len() != 2 || size != 8
                    || self.layout(self.operand_ty(&args[0].node))?.size.bytes() != 8
                    || self.layout(self.operand_ty(&args[1].node))?.size.bytes() != 8
                {
                    return Err("invalid ptr_mask signature".into());
                }
                let pointer = self.scalar(&args[0].node)?;
                let mask = self.scalar(&args[1].node)?;
                let value = self.bin(Binary::And, pointer, mask, 64, false).0;
                self.store(dest.address, value, 8)?;
            }
            "write_bytes" => {
                let address = self.scalar(&args[0].node)?;
                let value = self.scalar(&args[1].node)?;
                let count = self.scalar(&args[2].node)?;
                let scale = self.imm(self.layout(instance.args.type_at(0))?.size.bytes() as u128);
                let (size, overflow) = self.bin(Binary::Mul, count, scale, 64, false);
                self.code.push(Op::Assert {
                    value: overflow,
                    expected: false,
                    message: "fill size overflow".into(),
                });
                self.code.push(Op::FillBytes {
                    address,
                    value,
                    size,
                });
            }
            "size_of_val" | "align_of_val" => {
                let ty = instance.args.type_at(0);
                let metadata = if self.layout(ty)?.is_sized() {
                    None
                } else {
                    let pointer = self.operand(&args[0].node)?;
                    let metadata_at = self.add(pointer, 8);
                    Some(self.load(metadata_at, 8)?)
                };
                let (dynamic_size, dynamic_align) = self.dynamic_layout(ty, metadata)?;
                let value = if name == "size_of_val" { dynamic_size } else { dynamic_align };
                self.store(dest.address, value, size)?;
            }
            "vtable_size" | "vtable_align" => {
                let table=self.scalar(&args[0].node)?;
                let field=self.add(table,if name=="vtable_size" {8} else {16});
                let value=self.load(field,8)?;
                self.store(dest.address,value,size)?;
            }
            "compare_bytes" | "raw_eq" => {
                let left = self.scalar(&args[0].node)?;
                let right = self.scalar(&args[1].node)?;
                let count = if name == "raw_eq" {
                    self.imm(self.layout(instance.args.type_at(0))?.size.bytes() as u128)
                } else {
                    self.scalar(&args[2].node)?
                };
                let dst = self.reg();
                self.code.push(Op::CompareBytes {
                    dst,
                    left,
                    right,
                    size: count,
                });
                let result = if name == "raw_eq" {
                    let zero = self.imm(0);
                    self.bin(Binary::Eq, dst, zero, 32, false).0
                } else {
                    dst
                };
                self.store(dest.address, result, size)?;
            }
            "exact_div" => {
                let (bits, signed) = self.integer(self.operand_ty(&args[0].node))?;
                let a = self.scalar(&args[0].node)?;
                let b = self.scalar(&args[1].node)?;
                let remainder = self.bin(Binary::Rem, a, b, bits, signed).0;
                let zero = self.imm(0);
                let exact = self.bin(Binary::Eq, remainder, zero, bits, false).0;
                self.code.push(Op::Assert {
                    value: exact,
                    expected: true,
                    message: "exact division has a nonzero remainder".into(),
                });
                let value = self.bin(Binary::Div, a, b, bits, signed).0;
                self.store(dest.address, value, size)?;
            }
            "saturating_add" | "saturating_sub" => {
                let (bits, signed) = self.integer(self.operand_ty(&args[0].node))?;
                let a = self.scalar(&args[0].node)?;
                let b = self.scalar(&args[1].node)?;
                let op = if name == "saturating_add" {
                    Binary::Add
                } else {
                    Binary::Sub
                };
                let (value, overflow) = self.bin(op, a, b, bits, signed);
                let bound = if signed {
                    let zero = self.imm(0);
                    let negative = self.bin(Binary::Lt, a, zero, bits, true).0;
                    let low = self.imm(1u128 << (bits - 1));
                    let high = self.imm((1u128 << (bits - 1)) - 1);
                    let bound = self.reg();
                    self.code.push(Op::Select {
                        dst: bound,
                        condition: negative,
                        yes: low,
                        no: high,
                    });
                    bound
                } else {
                    self.imm(if name == "saturating_add" {
                        u128::MAX >> (128 - bits)
                    } else {
                        0
                    })
                };
                let result = self.reg();
                self.code.push(Op::Select {
                    dst: result,
                    condition: overflow,
                    yes: bound,
                    no: value,
                });
                self.store(dest.address, result, size)?;
            }
            "integer_min" | "integer_max" => {
                let (bits, signed) = self.integer(self.operand_ty(&args[0].node))?;
                let a = self.scalar(&args[0].node)?;
                let b = self.scalar(&args[1].node)?;
                let condition = self.bin(Binary::Lt, a, b, bits, signed).0;
                let dst = self.reg();
                let (yes, no) = if name == "integer_min" {
                    (a, b)
                } else {
                    (b, a)
                };
                self.code.push(Op::Select {
                    dst,
                    condition,
                    yes,
                    no,
                });
                self.store(dest.address, dst, size)?;
            }
            "assert_inhabited" | "assert_zero_valid" | "assert_mem_uninitialized_valid" => {
                let requirement =
                    rustc_middle::ty::layout::ValidityRequirement::from_intrinsic(intrinsic.name)
                        .ok_or("missing validity requirement")?;
                let valid = self
                    .tcx()
                    .check_validity_requirement((
                        requirement,
                        env().as_query_input(instance.args.type_at(0)),
                    ))
                    .map_err(|e| format!("validity layout: {e:?}"))?;
                if !valid {
                    self.code.push(Op::Trap {
                        message: format!("{name}: invalid type initialization"),
                    });
                }
            }
            "select_unpredictable" => {
                let condition = self.scalar(&args[0].node)?;
                let yes = self.operand(&args[1].node)?;
                let no = self.operand(&args[2].node)?;
                let selected = self.reg();
                self.code.push(Op::Select { dst: selected, condition, yes, no });
                self.code.push(Op::Copy { dst: dest.address, src: selected, size });
            }
            "typed_swap_nonoverlapping" => {
                let left = self.scalar(&args[0].node)?;
                let right = self.scalar(&args[1].node)?;
                let bytes = self.layout(instance.args.type_at(0))?.size.bytes_usize();
                let saved = self.temporary(bytes);
                self.code.push(Op::Copy { dst: saved, src: left, size: bytes });
                self.code.push(Op::Copy { dst: left, src: right, size: bytes });
                self.code.push(Op::Copy { dst: right, src: saved, size: bytes });
            }
            "abort" => {
                self.code.push(Op::Trap { message: "guest process aborted".into() });
            }
            "is_val_statically_known" => {
                // This optimization hint explicitly permits either answer.
                // Guest execution uses the general runtime path.
                let value = self.imm(0);
                self.store(dest.address, value, size)?;
            }
            "likely" | "unlikely" | "black_box" => {
                let src = self.operand(&args[0].node)?;
                self.code.push(Op::Copy {
                    dst: dest.address,
                    src,
                    size,
                });
            }
            "size_of" | "min_align_of" => {
                let layout = self.layout(instance.args.type_at(0))?;
                let value = self.imm(if name == "size_of" {
                    layout.size.bytes()
                } else {
                    layout.align.abi.bytes()
                } as u128);
                self.store(dest.address, value, size)?;
            }
            "transmute" => {
                let src = self.operand(&args[0].node)?;
                if self
                    .layout(self.operand_ty(&args[0].node))?
                    .size
                    .bytes_usize()
                    != size
                {
                    return Err("intrinsic transmute size".into());
                }
                self.code.push(Op::Copy {
                    dst: dest.address,
                    src,
                    size,
                });
            }
            "assume" => {
                let value = self.scalar(&args[0].node)?;
                self.code.push(Op::Assert {
                    value,
                    expected: true,
                    message: "assume".into(),
                });
            }
            "ub_checks" | "contract_checks" => {
                let enabled = if name == "ub_checks" {
                    self.tcx().sess.ub_checks()
                } else {
                    self.tcx().sess.contract_checks()
                };
                let value = self.imm(enabled as u128);
                self.store(dest.address, value, size)?;
            }
            // Some intrinsics provide an ordinary Rust implementation which
            // backends are explicitly allowed to execute. Lower that body
            // through our normal call path; mandatory shims still fail here.
            _ if !intrinsic.must_be_overridden => return Ok(false),
            _ => return Err(format!("unsupported intrinsic {name}")),
        }
        Ok(true)
    }
    fn lower(mut self) -> Result<Function> {
        let reachable = self.reachable_blocks()?;
        for (bb, block) in self.body.basic_blocks.iter_enumerated() {
            self.blocks[bb.as_usize()] = self.code.len();
            if !reachable[bb.as_usize()] {
                // Keep branch fixups total, including invalid discriminants.
                // No valid execution under panic-as-trap can enter this block.
                self.code.push(Op::Trap { message: "unreachable MIR block".into() });
                continue;
            }
            if let TerminatorKind::Call { func, .. } = &block.terminator().kind {
                if let ty::FnDef(def, _) = *self.operand_ty(func).kind() {
                    if let Some(name) = panic_function(self.tcx(), def) {
                        if block.statements.iter().all(panic_preparation) {
                            let location = self.tcx().sess.source_map().span_to_diagnostic_string(
                                block.terminator().source_info.span.source_callsite(),
                            );
                            self.code.push(Op::Trap {
                                message: format!("{name} at {location}"),
                            });
                            continue;
                        }
                    }
                }
            }
            for (statement_index, statement) in block.statements.iter().enumerate() {
                let emitted_start = self.code.len();
                match &statement.kind {
                    StatementKind::Intrinsic(intrinsic) => match &**intrinsic {
                        mir::NonDivergingIntrinsic::Assume(operand) => {
                            let value = self.scalar(operand)?;
                            self.code.push(Op::Assert {
                                value,
                                expected: true,
                                message: "MIR assume".into(),
                            });
                        }
                        mir::NonDivergingIntrinsic::CopyNonOverlapping(copy) => {
                            let src = self.scalar(&copy.src)?;
                            let dst = self.scalar(&copy.dst)?;
                            let count = self.scalar(&copy.count)?;
                            let ty = self
                                .operand_ty(&copy.src)
                                .builtin_deref(true)
                                .ok_or("copy pointee")?;
                            let scale = self.imm(self.layout(ty)?.size.bytes() as u128);
                            let (size, overflow) = self.bin(Binary::Mul, count, scale, 64, false);
                            self.code.push(Op::Assert {
                                value: overflow,
                                expected: false,
                                message: "copy size overflow".into(),
                            });
                            self.code.push(Op::CopyDynamic { dst, src, size });
                        }
                    },
                    StatementKind::Assign(assignment) => {
                        self.assign(assignment.0, &assignment.1)?
                    }
                    StatementKind::SetDiscriminant {
                        place,
                        variant_index,
                    } => {
                        let loc = self.place(**place)?;
                        self.set_discriminant(loc, *variant_index)?;
                    }
                    StatementKind::StorageLive(_)
                    | StatementKind::StorageDead(_)
                    | StatementKind::Nop
                    | StatementKind::PlaceMention(..)
                    | StatementKind::AscribeUserType(..)
                    | StatementKind::FakeRead(..)
                    | StatementKind::Coverage(..) => {}
                    other => return Err(format!("unsupported statement {other:?}")),
                }
                scalar_frame::byte_writes::remember(&mut self, bb.as_usize(), statement_index, emitted_start);
            }
            let emitted_start = self.code.len();
            match &block.terminator().kind {
                TerminatorKind::Goto { target } => self.jump(*target),
                TerminatorKind::SwitchInt { discr, targets } => {
                    let value = self.scalar(discr)?;
                    self.fixups.push(self.code.len());
                    self.code.push(Op::Switch {
                        value,
                        cases: targets.iter().map(|(v, t)| (v, t.as_usize())).collect(),
                        otherwise: targets.otherwise().as_usize(),
                    });
                }
                TerminatorKind::Return => self.code.push(Op::Return),
                TerminatorKind::Unreachable => self.code.push(Op::Trap {
                    message: "unreachable".into(),
                }),
                TerminatorKind::Assert {
                    cond,
                    expected,
                    msg,
                    target,
                    ..
                } => {
                    let value = self.scalar(cond)?;
                    self.code.push(Op::Assert {
                        value,
                        expected: *expected,
                        message: format!("{msg:?}"),
                    });
                    self.jump(*target);
                }
                TerminatorKind::Call {
                    func,
                    args,
                    destination,
                    target,
                    fn_span,
                    ..
                } => {
                    // For method syntax rustc points at the method name, not
                    // the receiver expression covered by the terminator span.
                    let source_info = mir::SourceInfo { span: *fn_span, ..block.terminator().source_info };
                    if matches!(self.operand_ty(func).kind(), ty::FnPtr(..)) {
                        let callee = self.scalar(func)?;
                        let (arguments, arg_sizes) = self.call_arguments(func, args)?;
                        let destination = self.place(*destination)?;
                        let result_size = self.layout(destination.ty)?.size.bytes_usize();
                        self.exporter.require_indirect_calls(CallShape {
                            args: arg_sizes.clone(),
                            result: result_size,
                        });
                        self.code.push(Op::CallIndirect {
                            callee,
                            args: arguments,
                            arg_sizes,
                            destination: destination.address,
                            result_size,
                        });
                        if let Some(target) = target {
                            self.jump(*target);
                        } else {
                            self.code.push(Op::Trap {
                                message: "diverging indirect call returned".into(),
                            });
                        }
                        continue;
                    }
                    let ty::FnDef(def, args_ty) = *self.operand_ty(func).kind() else {
                        return Err("indirect or virtual calls are not yet supported".into());
                    };
                    let instance = Instance::try_resolve(
                        self.tcx(),
                        env(),
                        def,
                        self.tcx().instantiate_bound_regions_with_erased(args_ty),
                    )
                    .map_err(|e| format!("resolve: {e:?}"))?
                    .ok_or("unresolved function instance")?;
                    if let ty::InstanceKind::Virtual(_,slot)=instance.def {
                        self.virtual_call(slot,func,args,*destination,
                            instance.def.requires_caller_location(self.tcx()), source_info)?;
                        if let Some(target)=target {self.jump(*target);} else {
                            self.code.push(Op::Trap{message:"diverging virtual call returned".into()});
                        }
                        continue;
                    }
                    if let Some(name) = panic_function(self.tcx(), def) {
                        let location = self.tcx().sess.source_map().span_to_diagnostic_string(
                            block.terminator().source_info.span.source_callsite(),
                        );
                        self.code.push(Op::Trap {
                            message: format!("{name} at {location}"),
                        });
                    } else {
                        if !self.system_function(instance, args, *destination)?
                            && !self.allocation_function(instance, args, *destination)?
                            && !self.intrinsic(instance, args, *destination, source_info)?
                        {
                            if self.exporter.trap_unsupported_calls && self.tcx().is_foreign_item(instance.def_id()) {
                                // MIR has already evaluated argument expressions. Preserve
                                // their place materialization, then stop before the foreign
                                // boundary. Never fabricate a return value or host call.
                                let _ = self.call_arguments(func, args)?;
                                self.trap_unavailable_call(UnavailableCallKind::Foreign,
                                    self.tcx().symbol_name(instance).name.to_owned());
                                continue;
                            }
                            let instance = if let ty::InstanceKind::Intrinsic(def) = instance.def {
                                let intrinsic = self.tcx().intrinsic(def).ok_or("missing intrinsic definition")?;
                                if intrinsic.must_be_overridden {
                                    return Err(format!("intrinsic {} requires a runtime shim", intrinsic.name));
                                }
                                // instance_mir(Intrinsic) has no body. Item
                                // requests the compiler-provided Rust body.
                                Instance { def: ty::InstanceKind::Item(def), args: instance.args }
                            } else { instance };
                            let function = self.exporter.register(instance);
                            let (mut arguments, _) = self.call_arguments(func, args)?;
                            if instance.def.requires_caller_location(self.tcx()) {
                                arguments.push(self.caller_argument(source_info)?);
                            }
                            let destination = self.place(*destination)?.address;
                            self.code.push(Op::Call {
                                function,
                                args: arguments,
                                destination,
                            });
                        }
                        if let Some(target) = target {
                            self.jump(*target);
                        } else {
                            self.code.push(Op::Trap {
                                message: "diverging function returned".into(),
                            });
                        }
                    }
                }
                TerminatorKind::Drop { place, target, .. } => {
                    let ty = self.mono(place.ty(&self.body.local_decls, self.tcx()).ty);
                    if ty.needs_drop(self.tcx(), env()) {
                        let loc = self.place(*place)?;
                        if matches!(ty.kind(),ty::Dynamic(..)) {
                            self.drop_dynamic(loc)?;
                            self.jump(*target);
                            continue;
                        }
                        let instance = Instance::resolve_drop_glue(self.tcx(), ty);
                        let function = self.exporter.register(instance);
                        let pointer = self.temporary(if loc.metadata.is_some() {16} else {8});
                        self.store(pointer, loc.address, 8)?;
                        if let Some(metadata)=loc.metadata {
                            let at=self.add(pointer,8);
                            self.store(at,metadata,8)?;
                        }
                        let destination = self.imm(0);
                        let mut arguments = vec![pointer];
                        if instance.def.requires_caller_location(self.tcx()) {
                            arguments.push(self.caller_argument(block.terminator().source_info)?);
                        }
                        self.code.push(Op::Call {
                            function,
                            args: arguments,
                            destination,
                        });
                    }
                    self.jump(*target);
                }
                TerminatorKind::UnwindResume | TerminatorKind::UnwindTerminate(..) => {
                    self.code.push(Op::Trap {
                        message: "unwinding is not yet supported".into(),
                    })
                }
                other => return Err(format!("unsupported terminator {other:?}")),
            }
            scalar_frame::byte_writes::remember(&mut self, bb.as_usize(), block.statements.len(), emitted_start);
        }
        for &index in &self.fixups {
            match &mut self.code[index] {
                Op::Jump { target } => *target = self.blocks[*target],
                Op::Switch {
                    cases, otherwise, ..
                } => {
                    *otherwise = self.blocks[*otherwise];
                    for (_, t) in cases {
                        *t = self.blocks[*t];
                    }
                }
                _ => return Err("internal branch fixup".into()),
            }
        }
        // Formal locals keep their offsets/alignment even when they occupy no
        // bytes. Elision changes the call interface, not the callee's storage.
        let mut arguments = Vec::new();
        for local in self.body.args_iter() {
            let slot = self.locals[local.as_usize()];
            if Some(local) == self.body.spread_arg {
                let ty = self.mono(self.body.local_decls[local].ty);
                let ty::Tuple(fields) = ty.kind() else {
                    return Err("MIR spread argument must be a tuple".into());
                };
                let layout = self.layout(ty)?;
                for (index, ty) in fields.iter().enumerate() {
                    let size = self.layout(ty)?.size.bytes_usize();
                    if size != 0 {
                        arguments.push(Slot {
                            offset: slot.offset + self.field_offset(layout, index)?,
                            size,
                        });
                    }
                }
            } else if slot.size != 0 {
                arguments.push(slot);
            }
        }
        if let Some(caller) = self.caller_location { arguments.push(caller); }
        let observed = scalar_frame::byte_writes::capture(&mut self);
        self.exporter.byte_writes.push(observed);
        scalar_promote::apply(&mut self)?;
        Ok(Function {
            name: format!(
                "{}{:?}",
                self.tcx().def_path_str(self.instance.def_id()),
                self.instance.args
            ),
            frame_size: self.frame_size,
            frame_align: self.frame_align,
            registers: self.registers as usize,
            args: arguments,
            result: self.locals[0],
            code: self.code,
        })
    }
}
