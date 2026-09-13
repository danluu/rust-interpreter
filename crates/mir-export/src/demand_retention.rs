//! Optional eviction of incremental query values not demanded this session.
//!
//! The checking graph and diagnostic replay remain rustc's. At finalization
//! stock rustc decodes undemanded green values only to serialize them again.
//! This mode omits that promotion pass and uses the stock result serializer.
//! Future value demands take rustc's normal missing-value recomputation path,
//! which verifies the original result fingerprint before accepting the value.
//!
//! Sparse values cannot be consumed by stock finalization: its promotion pass
//! assumes cacheable green values exist. Select a physically separate cache
//! directory BEFORE the compiler context exists, including for mode changes
//! and unsupported options. Never fall back to stock save inside that directory.
use crate::{borrowck_cache, demand_retention_format, wrapper_route::QueryCacheRetentionMode};
use rustc_data_structures::sync::par_join;
use rustc_interface::interface;
use rustc_middle::query::on_disk_cache::OnDiskCache;
use rustc_middle::ty::TyCtxt;
use rustc_middle::util::Providers;
use rustc_serialize::Encoder;
use rustc_serialize::opaque::FileEncoder;
use rustc_session::Session;
use std::fs;
use std::sync::{
    Mutex, OnceLock,
    atomic::{AtomicBool, AtomicU64, Ordering},
};

type Override = fn(&Session, &mut Providers);
static REQUESTED: AtomicBool = AtomicBool::new(false);
static INSTALLED: AtomicBool = AtomicBool::new(false);
static PREVIOUS_OVERRIDE: OnceLock<Option<Override>> = OnceLock::new();
static REPORT: Mutex<Option<serde_json::Value>> = Mutex::new(None);
static PROMOTION_PASSES_OMITTED: AtomicU64 = AtomicU64::new(0);
static SERIALIZED_BYTES: AtomicU64 = AtomicU64::new(0);
static SIDE_EFFECTS: AtomicU64 = AtomicU64::new(0);
static SERIALIZATION_ATTEMPTS: AtomicU64 = AtomicU64::new(0);
static SERIALIZER_QUERY_JOBS: AtomicU64 = AtomicU64::new(0);

pub(crate) fn configure(config: &mut interface::Config, mode: QueryCacheRetentionMode) {
    if mode == QueryCacheRetentionMode::Off {
        return;
    }
    assert!(
        !REQUESTED.swap(true, Ordering::Relaxed),
        "query retention configured twice"
    );
    let options = &config.opts.unstable_opts;
    let disabled = if config.opts.incremental.is_none() {
        Some("incremental compilation is disabled")
    } else if options.dump_dep_graph || options.query_dep_graph || options.incremental_verify_ich {
        Some("incremental compiler diagnostics requested")
    } else if options.codegen_backend.is_some() || config.make_codegen_backend.is_some() {
        Some("nonstandard codegen backend")
    } else if std::env::var_os("RUSTC_FORCE_RUSTC_VERSION").is_some() {
        Some("forced compiler cache version")
    } else if config
        .override_queries
        .is_some_and(|previous| !borrowck_cache::owns_override(previous))
    {
        Some("unreviewed compiler query override")
    } else {
        None
    };
    let original = config.opts.incremental.clone();
    if disabled.is_none() {
        config.opts.incremental = original
            .as_deref()
            .map(demand_retention_format::incremental_directory);
        assert!(
            PREVIOUS_OVERRIDE
                .set(config.override_queries.take())
                .is_ok()
        );
        config.override_queries = Some(install);
    }
    *REPORT.lock().unwrap() = Some(serde_json::json!({
        "schema_version": 1,
        "mode": "demand",
        "process_id": std::process::id(),
        "crate_name": config.opts.crate_name,
        "test": config.opts.test,
        "original_incremental_directory": original,
        "effective_incremental_directory": config.opts.incremental,
        "disabled_reason": disabled,
        "strict_checking": true,
        "cache_format": "stock rustc RSIC and OnDiskCache serialization",
        "retention": "values computed or loaded by the current compilation; tracked side effects retained",
    }));
}

fn install(session: &Session, providers: &mut Providers) {
    if let Some(previous) = PREVIOUS_OVERRIDE.get().copied().flatten() {
        previous(session, providers);
    }
    // Compare with the exact table from which this compiler's providers were
    // copied. Calling rustc_incremental::provide again can produce a distinct
    // function address for its closure across codegen units.
    let standard = &*rustc_interface::DEFAULT_QUERY_PROVIDERS;
    // Supported configurations were selected before the namespace was opened.
    // Unexpected provider changes are an adapter invariant failure. Running the
    // standard save hook here could corrupt the namespace contract, so fail
    // before analysis or publication instead of attempting that fallback.
    if !std::ptr::fn_addr_eq(
        providers.hooks.save_dep_graph,
        standard.hooks.save_dep_graph,
    ) {
        session
            .dcx()
            .fatal("query retention: unexpected incremental save provider");
    }
    providers.hooks.save_dep_graph = save_dep_graph;
    INSTALLED.store(true, Ordering::Relaxed);
}

fn save_dep_graph(tcx: TyCtxt<'_>) {
    tcx.sess.time("serialize_dep_graph", || tcx.dep_graph.with_ignore(|| {
        let session = tcx.sess;
        if session.opts.incremental.is_none()
            || session.dcx().has_errors_or_delayed_bugs().is_some() {
            return;
        }
        // These are exactly the gates making the pinned assert_dep_graph and
        // check_clean_annotations functions no-ops. They were rejected before
        // selecting the sparse namespace; never switch save routines here.
        assert!(!session.opts.unstable_opts.dump_dep_graph);
        assert!(!session.opts.unstable_opts.query_dep_graph);
        assert!(!session.opts.unstable_opts.incremental_verify_ich);
        let incremental = tcx.incr_comp_session.expect("incremental session for query retention");
        let path = |name| rustc_incremental::in_incr_comp_dir_sess(incremental, name);
        let graph = path("dep-graph.bin");
        let staging_graph = path("dep-graph.part.bin");
        let query_cache = path("query-cache.bin");
        let staged_query_cache = path(&format!("query-cache.demand-{}.new", std::process::id()));

        // Keep rustc's ordering and parallelism. TyCtxt::finish still checks
        // query keys and finishes graph encoding after this hook. The ordinary
        // compiler still commits or discards the working session directory.
        par_join(
            || session.time("incr_comp_persist_dep_graph", || {
                if let Err(error) = fs::rename(&staging_graph, &graph) {
                    session.dcx().err(format!(
                        "query retention: cannot move dependency graph from {} to {}: {error}",
                        staging_graph.display(), graph.display()));
                }
            }),
            || session.time("incr_comp_persist_result_cache", || {
                let cache = tcx.query_system.on_disk_cache.as_ref()
                    .expect("incremental query cache for query retention");
                // This is the sole intended change from stock save_dep_graph:
                // do not call tcx.dep_graph.exec_cache_promotions(tcx).
                PROMOTION_PASSES_OMITTED.fetch_add(1, Ordering::Relaxed);
                // Forced versions were declined in configure(). cfg_version
                // is therefore precisely the pinned file-format version source.
                let header = demand_retention_format::header(session.cfg_version)
                    .unwrap_or_else(|error| session.dcx().fatal(error));
                let mut attempts = 0;
                let position = session.time("incr_comp_serialize_result_cache", || loop {
                    // Memoized queries in the reviewed encoder converge. A
                    // bounded failure reports an adapter invariant violation;
                    // it never publishes a partially stabilized cache.
                    if attempts == 16 {
                        session.dcx().fatal("query retention: cache serialization did not stabilize after 16 passes");
                    }
                    attempts += 1;
                    // A serializer can demand a value, e.g. static allocation
                    // encoding asks codegen_fn_attrs whether the static is TLS.
                    // Keep the previous mmap alive until a full pass starts no
                    // query jobs. Then its source/side-effect indexes and query
                    // values describe one complete, stable compiler state.
                    // This depends on the pinned encoder contract: value
                    // encoders only queue allocation IDs while query-cache
                    // shards are borrowed. TLS-attribute queries occur in the
                    // later allocation loop, after those borrows are released.
                    // Job counting does not make an arbitrary reentrant
                    // future compiler encoder safe; toolchain upgrades need
                    // a fresh audit of that ordering.
                    let before = serialization_state(tcx);
                    remove_cache_file(session, &staged_query_cache);
                    let mut encoder = FileEncoder::new(&staged_query_cache).unwrap_or_else(|error| {
                        session.dcx().fatal(format!(
                            "query retention: cannot create query cache {}: {error}", staged_query_cache.display()))
                    });
                    encoder.emit_raw_bytes(&header);
                    SERIALIZATION_ATTEMPTS.fetch_add(1, Ordering::Relaxed);
                    let position = OnDiskCache::serialize(tcx, encoder).unwrap_or_else(|(path, error)| {
                        session.dcx().fatal(format!(
                            "query retention: cannot write query cache {}: {error}", path.display()))
                    });
                    if let Some(error) = session.dcx().has_errors_or_delayed_bugs() {
                        error.raise_fatal();
                    }
                    let after = serialization_state(tcx);
                    SERIALIZER_QUERY_JOBS.fetch_add(after.0 - before.0, Ordering::Relaxed);
                    if before == after { break position; }
                    // The completed file is only a staging attempt. The next
                    // pass includes newly materialized values and side effects;
                    // no old or incomplete artifact is accepted or published.
                });

                // The working file may hard-link the prior successful session.
                // Close its mmap and unlink it; NEVER truncate the shared inode.
                cache.close_serialized_data_mmap();
                remove_cache_file(session, &query_cache);
                fs::rename(&staged_query_cache, &query_cache).unwrap_or_else(|error| {
                    session.dcx().fatal(format!(
                        "query retention: cannot publish query cache {}: {error}", query_cache.display()))
                });
                SERIALIZED_BYTES.store(position as u64, Ordering::Relaxed);
                SIDE_EFFECTS.store(tcx.query_system.side_effects.borrow().len() as u64,
                    Ordering::Relaxed);
                session.prof.artifact_size("query_cache", "query-cache.bin", position as u64);
            }),
        );
    }));
}

fn serialization_state(tcx: TyCtxt<'_>) -> (u64, usize, usize, usize) {
    (
        tcx.query_system.jobs.load(Ordering::Relaxed),
        tcx.query_system.side_effects.borrow().len(),
        tcx.query_system.used_features.borrow().len(),
        tcx.sess.source_map().files().len(),
    )
}

fn remove_cache_file(session: &Session, path: &std::path::Path) {
    match fs::remove_file(path) {
        Ok(()) => {}
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => session.dcx().fatal(format!(
            "query retention: cannot remove old query cache {}: {error}",
            path.display()
        )),
    }
}

pub(crate) fn report() {
    let Some(mut report) = REPORT.lock().unwrap().clone() else {
        return;
    };
    report["provider_installed"] = INSTALLED.load(Ordering::Relaxed).into();
    report["promotion_passes_omitted"] = PROMOTION_PASSES_OMITTED.load(Ordering::Relaxed).into();
    report["serialized_bytes"] = SERIALIZED_BYTES.load(Ordering::Relaxed).into();
    report["retained_side_effects"] = SIDE_EFFECTS.load(Ordering::Relaxed).into();
    report["serialization_attempts"] = SERIALIZATION_ATTEMPTS.load(Ordering::Relaxed).into();
    report["serializer_query_jobs"] = SERIALIZER_QUERY_JOBS.load(Ordering::Relaxed).into();
    eprintln!("rust-interp-query-cache-retention: {report}");
}
