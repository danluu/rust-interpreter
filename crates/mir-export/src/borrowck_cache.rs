//! Reconstruct one finite query result from rustc's own incremental proof.
//!
//! `mir_borrowck` has no on-disk value cache. A normal value-demanding query
//! therefore reruns its provider even after rustc has proved its inputs green.
//! We can reconstruct `Ok(empty hidden-types map)` when its exact compiler
//! fingerprint matches the previous result. No compiler-owned types, IDs or
//! arenas survive sessions, and no separate eligibility cache can become stale.
//! Aggregate analysis, query diagnostic replay and finalization remain rustc's.
use crate::wrapper_route::BorrowckCacheMode;
use rustc_data_structures::fx::FxIndexMap;
use rustc_driver::{Callbacks, Compilation};
use rustc_hir::def_id::LocalDefId;
use rustc_interface::interface;
use rustc_middle::dep_graph::{DepKind, DepNode};
use rustc_middle::query::erase::erase_val;
use rustc_middle::ty::TyCtxt;
use rustc_middle::util::Providers;
use rustc_session::{Session, config::Polonius};
use std::sync::{Mutex, OnceLock, atomic::{AtomicU64, Ordering}};

type BorrowckResult<'tcx> = rustc_middle::queries::mir_borrowck::ProvidedValue<'tcx>;
type Provider = for<'tcx> fn(TyCtxt<'tcx>, LocalDefId) -> BorrowckResult<'tcx>;

static MODE: OnceLock<BorrowckCacheMode> = OnceLock::new();
static ORIGINAL: OnceLock<Provider> = OnceLock::new();
static COMPILATION: OnceLock<serde_json::Value> = OnceLock::new();
static DISABLED: Mutex<Option<&'static str>> = Mutex::new(None);
static PROVIDER_CALLS: AtomicU64 = AtomicU64::new(0);
static GREEN_CANDIDATES: AtomicU64 = AtomicU64::new(0);
static FINGERPRINT_MATCHES: AtomicU64 = AtomicU64::new(0);
static FINGERPRINT_MISSES: AtomicU64 = AtomicU64::new(0);
static REUSED: AtomicU64 = AtomicU64::new(0);
static VERIFIED: AtomicU64 = AtomicU64::new(0);

fn increment(counter: &AtomicU64) { counter.fetch_add(1, Ordering::Relaxed); }

pub(crate) fn configure(config: &mut interface::Config, mode: BorrowckCacheMode) {
    if mode == BorrowckCacheMode::Off { return; }
    // Our entry points run exactly one compiler session per process. Never
    // compose this optimization with an unreviewed provider override.
    assert!(MODE.set(mode).is_ok(), "borrowck cache configured twice");
    if config.override_queries.is_some() {
        *DISABLED.lock().unwrap() = Some("another query override is installed");
        return;
    }
    config.override_queries = Some(install);
}

fn install(session: &Session, providers: &mut Providers) {
    let _ = COMPILATION.set(serde_json::json!({
        "crate_name": session.opts.crate_name,
        "test": session.opts.test,
    }));
    let options = &session.opts.unstable_opts;
    let reason = if session.opts.incremental.is_none() {
        Some("incremental compilation is disabled")
    } else if options.dump_mir.is_some() || options.dump_mir_dataflow
        || options.dump_mir_graphviz || options.nll_facts || options.validate_mir {
        Some("compiler MIR diagnostics requested")
    } else if options.polonius != Polonius::default() {
        Some("nondefault borrow checker requested")
    } else { None };
    if let Some(reason) = reason {
        *DISABLED.lock().unwrap() = Some(reason);
        return;
    }
    let mut standard = Providers::default();
    rustc_borrowck::provide(&mut standard.queries);
    if !std::ptr::fn_addr_eq(providers.queries.mir_borrowck, standard.queries.mir_borrowck) {
        *DISABLED.lock().unwrap() = Some("nonstandard borrow-check provider");
        return;
    }
    assert!(ORIGINAL.set(providers.queries.mir_borrowck).is_ok());
    providers.queries.mir_borrowck = borrowck;
}

fn borrowck<'tcx>(tcx: TyCtxt<'tcx>, def: LocalDefId) -> BorrowckResult<'tcx> {
    let original = *ORIGINAL.get().expect("original borrow-check provider");
    // Internal diagnostic attributes can request additional provider output,
    // including attributes on nested closures. Decline the whole crate.
    let disabled = if !tcx.dep_graph.is_fully_enabled() {
        Some("incremental dependency tracking is disabled")
    } else if tcx.dcx().has_errors_or_delayed_bugs().is_some() {
        Some("compiler has errors")
    } else if tcx.features().rustc_attrs() {
        Some("internal compiler attributes enabled")
    } else { None };
    if let Some(reason) = disabled {
        *DISABLED.lock().unwrap() = Some(reason);
        increment(&PROVIDER_CALLS);
        return original(tcx, def);
    }
    let node = DepNode::construct(tcx, DepKind::mir_borrowck, &def);
    let query = &tcx.query_system.query_vtables.mir_borrowck;
    // Do not initiate green validation for the query whose provider is now
    // running. Rustc must already have proved it unchanged and replayed its
    // tracked side effects before we even inspect the previous value.
    if !tcx.dep_graph.is_green(&node) || query.eval_always {
        increment(&PROVIDER_CALLS);
        return original(tcx, def);
    }
    let Some(hash_value) = query.hash_value_fn else {
        increment(&PROVIDER_CALLS);
        return original(tcx, def);
    };
    increment(&GREEN_CANDIDATES);
    let Some((previous_index, _)) = tcx.dep_graph.try_mark_green(tcx, &node) else {
        increment(&PROVIDER_CALLS);
        return original(tcx, def);
    };
    let empty: BorrowckResult<'tcx> = Ok(tcx.arena.alloc(FxIndexMap::default()));
    let erased = erase_val(empty);
    let fingerprint = tcx.with_stable_hashing_context(|mut hcx| hash_value(&mut hcx, &erased));
    let previous = tcx.dep_graph.data().unwrap().prev_value_fingerprint_of(previous_index);
    if fingerprint != previous {
        increment(&FINGERPRINT_MISSES);
        increment(&PROVIDER_CALLS);
        return original(tcx, def);
    }
    increment(&FINGERPRINT_MATCHES);
    if MODE.get() == Some(&BorrowckCacheMode::Verify) {
        increment(&PROVIDER_CALLS);
        let result = original(tcx, def);
        if !matches!(result, Ok(types) if types.is_empty()) {
            tcx.dcx().fatal("borrowck cache verification: previous empty-result fingerprint disagrees with the original provider");
        }
        increment(&VERIFIED);
        result
    } else {
        increment(&REUSED);
        // Rustc's green-provider path also runs its usual result-fingerprint
        // consistency check. We rely on the same collision assumptions as
        // the compiler's ordinary incremental cache, not on a second proof.
        empty
    }
}

pub(crate) fn report() {
    let Some(mode) = MODE.get() else { return; };
    let read = |counter: &AtomicU64| counter.load(Ordering::Relaxed);
    eprintln!("rust-interp-borrowck-cache: {}", serde_json::json!({
        "schema_version": 1,
        "process_id": std::process::id(),
        "compilation": COMPILATION.get(),
        "mode": if *mode == BorrowckCacheMode::Verify { "verify" } else { "reuse" },
        "provider_calls": read(&PROVIDER_CALLS),
        "green_candidates": read(&GREEN_CANDIDATES),
        "fingerprint_matches": read(&FINGERPRINT_MATCHES),
        "fingerprint_misses": read(&FINGERPRINT_MISSES),
        "reused": read(&REUSED), "verified": read(&VERIFIED),
        "disabled_reason": *DISABLED.lock().unwrap(),
        "provider_wrapped": ORIGINAL.get().is_some(),
        "counter_scope": "calls observed by this override; bypassed providers are not counted",
        "checking": "ordinary rustc analysis; only proven-green successful empty query values reconstructed",
        "proof": "previous rustc result fingerprint and already-green dependency node",
        "persistent_sidecar": false,
    }));
}

pub(crate) struct CheckCallbacks(pub BorrowckCacheMode);
impl Callbacks for CheckCallbacks {
    fn config(&mut self, config: &mut interface::Config) { configure(config, self.0); }
    fn after_analysis<'tcx>(&mut self, _: &interface::Compiler, _: TyCtxt<'tcx>) -> Compilation {
        Compilation::Continue
    }
}
