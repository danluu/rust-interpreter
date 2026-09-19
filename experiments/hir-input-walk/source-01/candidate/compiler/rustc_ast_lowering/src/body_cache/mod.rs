//! Checked body capture and separately selected, fully verified replay.
use std::path::PathBuf;
use rustc_ast::{self as ast, node_id::NodeMap};
use rustc_data_structures::fingerprint::Fingerprint;
use rustc_hir as hir;
use rustc_hir::def::Res;
use rustc_middle::middle::resolve::ResolverAstLowering;
use rustc_middle::ty::TyCtxt;
use rustc_serialize::{Encodable, opaque::mem_encoder::MemEncoder};
use rustc_span::Span;
use crate::LoweringContext;

mod capture;
mod effects;
mod entry;
mod kinds;
mod prepared;
mod validate;
mod wire;
mod input;
mod journal;
mod storage;
mod source_identity;
pub(super) use effects::Trace;

const FORMAT: &str = "hir-body-capture-v2-cold-materialization-1";
const REUSE_POLICY: &str = "hir-body-reuse-v2-ready-hit-1";

pub(super) struct Candidate {
    owner: hir::OwnerId,
    body: ast::NodeId,
    name: String,
    key: Vec<u8>,
    path: PathBuf,
    ast_nodes: Vec<(ast::NodeId, bool)>,
    ordinals: NodeMap<u32>,
    nodes: Vec<journal::Node>,
    kinds: Vec<kinds::Kind>,
    resolutions: Vec<Option<Res<ast::NodeId>>>,
    current_span: Span,
    source: String,
    input_statistics: [usize; 6],
    // Cold-audit guard only; never enters the persistent key or payload.
    context_identity: [usize; 3],
}

fn hex(value: Fingerprint) -> String {
    let (a, b) = value.split();
    format!("{:016x}{:016x}", a.as_u64(), b.as_u64())
}

fn current_hir_arena_identity<'hir>(arenas: &rustc_data_structures::sync::WorkerLocal<hir::Arena<'hir>>) -> usize {
    // GlobalCtxt stores the WorkerLocal wrapper; LoweringContext stores its
    // current worker's Arena after this same deref coercion. Compare the Arena,
    // not the wrapper allocation, while retaining every later identity check.
    let arena: &hir::Arena<'hir> = arenas;
    arena as *const _ as usize
}

pub(super) fn prepare<'tcx>(tcx: TyCtxt<'tcx>, resolver: &ResolverAstLowering<'tcx>,
    owner: ast::NodeId, span: Span, function: &ast::Fn, role: &'static str) -> Option<Candidate> {
    if !(tcx.sess.opts.unstable_opts.hir_body_cache_capture || tcx.sess.opts.unstable_opts.hir_body_cache_reuse)
        || std::env::var_os("RUSTC_FORCE_RUSTC_VERSION").is_some() { return None; }
    let session = tcx.incr_comp_session?;
    let (probe, ast_nodes) = input::probe(tcx, resolver, owner, span, function, role).ok()?.into_parts();
    let mut ordinals = NodeMap::default();
    let mut nodes = Vec::with_capacity(ast_nodes.len());
    for (ordinal, &(id, body)) in ast_nodes.iter().enumerate() {
        ordinals.insert(id, ordinal as u32);
        let binding = resolver.partial_res_map.get(&id).and_then(|res| res.full_res())
            .is_some_and(|res| matches!(res, Res::Local(local) if local == id));
        nodes.push(journal::Node { body, binding, traits: resolver.owners[&owner].trait_map.contains_key(&id) });
    }
    let kinds = kinds::classify(function, &ordinals)?;
    let resolutions = ast_nodes.iter().map(|(id, _)|
        resolver.partial_res_map.get(id).and_then(|res| res.full_res())).collect();
    let mut encoder = MemEncoder::new();
    let policy = if tcx.sess.opts.unstable_opts.hir_body_cache_reuse { REUSE_POLICY } else { FORMAT };
    policy.encode(&mut encoder);
    source_identity::SOURCE_IDENTITY.encode(&mut encoder);
    cfg!(debug_assertions).encode(&mut encoder);
    tcx.sess.cfg_version.encode(&mut encoder);
    tcx.sess.opts.dep_tracking_hash(false).as_u64().encode(&mut encoder);
    probe.input.encode(&mut encoder);
    let key = encoder.finish();
    if key.len() > storage::MAX_RECORD / 2 { return None; }
    Some(Candidate {
        owner: hir::OwnerId { def_id: resolver.owners[&owner].def_id },
        body: function.body.as_deref()?.id, name: function.ident.name.as_str().to_owned(),
        path: session.session_directory.join(format!("{policy}-{}.json", hex(probe.input.owner.0))),
        key, ast_nodes, ordinals, nodes, kinds, resolutions, current_span: span,
        source: probe.input.owner_source.clone(),
        input_statistics: [probe.body_bytes, probe.body_nodes, probe.parameter_nodes,
            probe.trait_entries, probe.trait_candidates, probe.external_resolutions],
        context_identity: [tcx.sess as *const _ as usize, current_hir_arena_identity(tcx.hir_arena),
            resolver as *const _ as usize],
    })
}

fn report(lctx: &LoweringContext<'_, '_>, candidate: &Candidate, state: &str,
    start: u32, end: u32, events: usize) {
    if lctx.tcx.sess.opts.unstable_opts.incremental_info {
        let [bytes, ast, params, traits, candidates, externals] = candidate.input_statistics;
        eprintln!("[hir-body-capture] {} {state} S={start} E={end} events={events} cache_hits=0 body_codec=1 prepared_values=1 cold_materialization_audit=1 hit_materializer=0 \
            body_bytes={bytes} body_ast={ast} param_ast={params} trait_entries={traits} trait_candidates={candidates} external_refs={externals}",
            candidate.name);
    }
}

pub(super) fn lower<'hir>(lctx: &mut LoweringContext<'_, 'hir>, body: &ast::Block) -> hir::Expr<'hir> {
    let Some(candidate) = lctx.body_candidate.take() else { return lctx.lower_block_expr(body); };
    if candidate.owner != lctx.curr_owner.owner_id || candidate.body != body.id {
        return lctx.lower_block_expr(body);
    }
    let Some(frame) = effects::Frame::enter(lctx, &candidate) else {
        report(lctx, &candidate, "rejected-entry", 0, 0, 0);
        return lctx.lower_block_expr(body);
    };
    // Active crate features and actual allow arrays are captured here, after
    // stock parameters. prepare() may run before context/signature work.
    let Some(record_key) = entry::bind(lctx, &candidate.key) else {
        report(lctx, &candidate, "rejected-normalized-entry", frame.start, frame.start, 0);
        return lctx.lower_block_expr(body);
    };
    let entry = journal::Entry { start: frame.start, nodes: &candidate.nodes, prefix_bindings: &frame.prefix };
    if lctx.tcx.sess.opts.unstable_opts.hir_body_cache_reuse {
        if let Some(value) = prepared::try_reuse(lctx, &candidate, &record_key, &frame) {
            if lctx.tcx.sess.opts.unstable_opts.incremental_info {
                eprintln!("[hir-body-reuse] {} hit cache_hits=1 verify_tree=1 verify_journal=1 verify_poststate=1 S={} E={}", candidate.name,
                    frame.start, lctx.curr_owner.item_local_id_counter.as_u32());
            }
            return value;
        }
        frame.assert_unchanged_miss(lctx);
    }
    // Capture-only mode and replay misses both continue through ordinary
    // lowering. Reading/decoding below mutates no lowering state.
    let previous = storage::read(&candidate.path, &record_key).and_then(|payload| {
        let checked = journal::check(payload.journal.clone(), &entry)?;
        let current = validate::Current::new(&candidate, frame.start, &frame.prefix, &checked)?;
        let tree = validate::check(payload.tree.clone(), &current)?;
        let _prepared = prepared::prepare(&tree, &current)?;
        Some(payload)
    });
    lctx.body_trace = Some(Trace::new());
    let value = lctx.lower_block_expr(body); // Ordinary lowering on every miss.
    let trace = lctx.body_trace.take();
    let end = lctx.curr_owner.item_local_id_counter.as_u32();
    let captured = trace.and_then(|trace| trace.finish(&candidate, frame.start, end, value.hir_id))
        .and_then(|value| journal::check(value, &entry));
    let Some(checked) = captured.filter(|checked| frame.validate_exit(lctx, &candidate, checked).is_some()) else {
        report(lctx, &candidate, "rejected-effects", frame.start, end, 0);
        return value;
    };
    // Preserve the first failed boundary in incremental-info diagnostics. Every
    // check and its order remain the same; no rejected tree can be published.
    let captured_tree = (|| {
        let current = validate::Current::new(&candidate, frame.start, &frame.prefix, &checked)
            .ok_or("rejected-body-tree-current")?;
        let tree = capture::capture(&candidate, &current, &value)
            .ok_or("rejected-body-tree-capture")?;
        let tree = validate::check(tree, &current).ok_or("rejected-body-tree-validation")?;
        let prepared = prepared::prepare(&tree, &current).ok_or("rejected-body-tree-preparation")?;
        prepared::audit(lctx, &candidate, &tree, prepared).ok_or("rejected-body-tree-cold-audit")?;
        frame.validate_exit(lctx, &candidate, &checked).ok_or("rejected-body-tree-post-audit-exit")?;
        Ok(tree)
    })();
    let tree = match captured_tree {
        Ok(tree) => tree,
        Err(state) => {
            report(lctx, &candidate, state, frame.start, end, checked.journal().events.len());
            return value;
        }
    };
    let payload = storage::Payload { journal: checked.journal().clone(), tree: tree.tree().clone() };
    let state = match previous {
        Some(previous) if previous == payload => "same-tree-and-journal-after-stock-lowering",
        Some(_) => "changed-tree-or-journal-after-stock-lowering",
        None => "cold-tree-and-journal-after-stock-lowering",
    };
    // A record is written only after stock lowering, cold materialization/
    // recapture and exact exit checks, in the selected policy's own namespace.
    let stored = storage::write(&candidate.path, &record_key, &payload);
    report(lctx, &candidate, if stored { state } else { "tree-write-unavailable" },
        frame.start, end, checked.journal().events.len());
    value
}

impl LoweringContext<'_, '_> {
    pub(super) fn insert_body_binding(&mut self, id: ast::NodeId, local: hir::ItemLocalId) {
        let old = self.curr_owner.ident_and_label_to_local_id.insert(id, local);
        if let Some(trace) = &mut self.body_trace { trace.binding(id, old, local); }
    }
    pub(super) fn reject_body_capture(&mut self, reason: &'static str) {
        if let Some(trace) = &mut self.body_trace { trace.reject(reason); }
    }
}

#[cfg(test)]
mod tests {
    use super::current_hir_arena_identity;
    use rustc_data_structures::sync::{Registry, WorkerLocal};
    use rustc_hir as hir;
    use std::num::NonZero;

    #[test]
    fn candidate_identity_uses_worker_arena_and_rejects_wrapper_or_foreign_arena() {
        // Registry association is thread-local and cannot be replaced. Use a
        // fresh thread so this control is independent of other libtest cases.
        std::thread::spawn(|| {
            let registry = Registry::new(NonZero::new(1).unwrap());
            registry.register();
            let arenas = WorkerLocal::new(|_| hir::Arena::default());
            let other = WorkerLocal::new(|_| hir::Arena::default());
            let lowered: &hir::Arena<'_> = &arenas;
            let actual = current_hir_arena_identity(&arenas);
            assert_eq!(actual, lowered as *const _ as usize);
            assert_ne!(actual, &arenas as *const _ as usize);
            assert_ne!(actual, current_hir_arena_identity(&other));
            assert_eq!(actual, current_hir_arena_identity(&arenas));
        }).join().unwrap();
    }
}
