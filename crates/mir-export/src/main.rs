#![feature(rustc_private)]
extern crate rustc_abi;
extern crate rustc_ast;
extern crate rustc_borrowck;
extern crate rustc_data_structures;
extern crate rustc_driver;
extern crate rustc_hir;
extern crate rustc_incremental;
extern crate rustc_interface;
extern crate rustc_middle;
extern crate rustc_session;
extern crate rustc_span;

mod lower;
mod allocation_trace;
mod audit;
mod test_metadata;
mod names;
mod wrapper_route;
mod export_timings;
mod function_costs;
mod typed_relocations;
mod function_dependencies;
mod function_cache;
mod reuse_misses;
mod borrowck_cache;
mod native_driver;

use rustc_driver::{Callbacks, Compilation};
use rustc_interface::interface;
use rustc_middle::ty::TyCtxt;
use std::path::{Path, PathBuf};
use std::time::Instant;

struct Export {
    entries: Vec<String>,
    output: PathBuf,
    started: Instant,
    demand: bool,
    demand_cache: bool,
    audit_selection: Option<PathBuf>,
    list_tests: bool,
    test_filter: Option<test_metadata::Filter>,
    retain_audit_bodies: bool,
    test_body: bool,
    inline_leaves: bool,
    trap_unsupported_calls: bool,
    run_try_callbacks: bool,
    allocation_trace: bool,
    borrowck_cache: wrapper_route::BorrowckCacheMode,
}
impl Export {
    fn publish(&self, tcx: TyCtxt<'_>, bytes: &[u8], suffix: &str) -> Result<(), String> {
        self.publish_to(tcx, bytes, suffix, &self.output)
    }
    fn publish_to(&self, tcx: TyCtxt<'_>, bytes: &[u8], suffix: &str, output: &Path) -> Result<(), String> {
        let temp = output.with_extension(format!("tmp-{}", std::process::id()));
        std::fs::write(&temp, bytes).map_err(|e| e.to_string())?;
        std::fs::rename(&temp, output).map_err(|e| e.to_string())?;
        if !self.demand {
            if let rustc_session::config::OutFileName::Real(metadata) =
                rustc_session::output::filename_for_metadata(tcx.sess, tcx.output_filenames(())) {
                let mut sidecar = metadata.into_os_string(); sidecar.push(suffix);
                let sidecar = PathBuf::from(sidecar);
                let temp = sidecar.with_extension(format!("tmp-{}", std::process::id()));
                std::fs::write(&temp, bytes).map_err(|e| e.to_string())?;
                std::fs::rename(temp, sidecar).map_err(|e| e.to_string())?;
            }
        }
        Ok(())
    }
    fn emit<'tcx>(&mut self, tcx: TyCtxt<'tcx>) -> Compilation {
        let checked = Instant::now();
        let mut timings = export_timings::Timings::new("emit");
        if self.list_tests {
            let report = test_metadata::Index::new(tcx).list()
                .unwrap_or_else(|error| tcx.dcx().fatal(format!("cannot discover tests: {error}")));
            let bytes = serde_json::to_vec(&report).expect("serialize test discovery");
            if bytes.len() > 8 * 1024 * 1024 {
                tcx.dcx().fatal("test discovery report exceeds 8 MiB");
            }
            if let Err(error) = self.publish(tcx, &bytes, ".tests.json") {
                tcx.dcx().fatal(format!("cannot publish test discovery: {error}"));
            }
            return Compilation::Continue;
        }
        if self.audit_selection.is_some() {
            let report = audit::report(tcx, &self.entries,
                self.retain_audit_bodies.then_some(self.output.as_path()), self.inline_leaves, self.trap_unsupported_calls, self.run_try_callbacks)
                .unwrap_or_else(|error| tcx.dcx().fatal(format!("cannot retain lowering audit: {error}")));
            let bytes = serde_json::to_vec(&report).expect("serialize lowering audit");
            if let Err(error) = self.publish(tcx, &bytes, ".audit.json") {
                tcx.dcx().fatal(format!("cannot publish lowering audit: {error}"));
            }
            return Compilation::Continue;
        }
        let mut selection = self.test_filter.as_ref().map(|filter| {
            let listing = test_metadata::Index::new(tcx).list()
                .unwrap_or_else(|error| tcx.dcx().fatal(format!("cannot select tests: {error}")));
            let (entries, report) = filter.select(listing)
                .unwrap_or_else(|error| tcx.dcx().fatal(error));
            self.entries = entries;
            report
        });
        match lower::export(tcx, &self.entries, self.demand, self.test_body, self.inline_leaves,
                            self.trap_unsupported_calls, self.run_try_callbacks, self.allocation_trace, self.test_filter.is_some()).and_then(|mut exported| {
            timings.checkpoint("lower_graph");
            let program = &exported.program;
            rust_interp_bytecode::validate(&program)?;
            timings.checkpoint("validation");
            let bytes = bincode::serialize(&program).map_err(|e| e.to_string())?;
            timings.checkpoint("serialization");
            use sha2::Digest;
            let artifact_sha256 = (self.allocation_trace || self.trap_unsupported_calls || !exported.selected_entries.is_empty())
                .then(|| format!("{:x}", sha2::Sha256::digest(&bytes)));
            timings.checkpoint("artifact_hash");
            // Finish the bounded trace before publishing any successful output.
            let trace = match exported.allocation_trace.take() {
                Some(trace) => {
                    Some(trace.finish(artifact_sha256.as_deref().ok_or("missing trace digest")?)?)
                }
                None => None,
            };
            timings.checkpoint("trace_hash_and_finalize");
            let costs = exported.function_costs.take()
                .map(|costs| costs.finish(program, &bytes)).transpose()?;
            timings.checkpoint("function_costs_finalize");
            // Associate bytecode with Cargo's exact metadata artifact, including
            // configuration reverts that reuse a previous artifact directly.
            self.publish(tcx, &bytes, ".rbc")?;
            timings.checkpoint("bytecode_publication");
            if !exported.selected_entries.is_empty() {
                let entries = exported.selected_entries.iter().map(|(name, function)| {
                    Ok(rust_interp_bytecode::SelectedEntry { name: name.clone(), function: *function,
                        body_name: program.functions.get(*function).ok_or("selected entry disappeared during optimization")?.name.clone() })
                }).collect::<Result<Vec<_>, String>>()?;
                let catalog = rust_interp_bytecode::EntryCatalog::new(program,
                    artifact_sha256.clone().ok_or("missing entry catalog digest")?, entries)?;
                let mut output = self.output.as_os_str().to_owned(); output.push(".entries.json");
                self.publish_to(tcx, &serde_json::to_vec(&catalog).map_err(|e| e.to_string())?,
                    ".rbc.entries.json", Path::new(&output))?;
            }
            timings.checkpoint("entry_catalog_publication");
            if let Some(report) = &mut selection {
                report["artifact_sha256"] = serde_json::json!(artifact_sha256.as_ref().ok_or("missing selection digest")?);
                let bytes = serde_json::to_vec(report).map_err(|e| e.to_string())?;
                if bytes.len() > 8 * 1024 * 1024 { return Err("test selection report exceeds 8 MiB".into()); }
                let mut output = self.output.as_os_str().to_owned(); output.push(".selection.json");
                self.publish_to(tcx, &bytes, ".rbc.selection.json", Path::new(&output))?;
            }
            timings.checkpoint("test_selection_publication");
            if self.trap_unsupported_calls {
                timings.checkpoint("call_report_setup");
                let report = serde_json::json!({"kind":"unavailable-calls","schema_version":1,
                    "trap_unsupported_calls":true,"run_try_callbacks":self.run_try_callbacks,"strict_frontend":!self.demand,
                    "artifact_sha256":artifact_sha256,
                    "unavailable_calls":exported.unavailable_calls()});
                let mut output = self.output.as_os_str().to_owned();
                output.push(".calls.json");
                self.publish_to(tcx, &serde_json::to_vec(&report).map_err(|e|e.to_string())?,
                    ".rbc.calls.json", Path::new(&output))?;
            }
            timings.checkpoint("call_report_and_publication");
            if let Some(trace) = trace {
                self.publish_to(tcx, &trace, ".rbc.allocations.jsonl", &allocation_trace_path(&self.output))?;
            }
            timings.checkpoint("trace_publication");
            if let Some(costs) = costs {
                eprintln!("rust-interp-function-costs: {costs}");
            }
            eprintln!("rust-interp-export: frontend_ms={:.3} lowering_ms={:.3} functions={} ops={} bytes={}",
                checked.duration_since(self.started).as_secs_f64() * 1000.0,
                checked.elapsed().as_secs_f64() * 1000.0,
                program.functions.len(), program.functions.iter().map(|f| f.code.len()).sum::<usize>(), bytes.len());
            timings.checkpoint("summary_reporting");
            Ok(())
        }) {
            Ok(()) => {
                timings.finish();
                if self.demand { Compilation::Stop } else { Compilation::Continue }
            },
            Err(error) => tcx.dcx().fatal(format!("custom interpreter cannot lower this entry: {error}")),
        }
    }
}
impl Callbacks for Export {
    fn config(&mut self, config: &mut interface::Config) {
        borrowck_cache::configure(config, self.borrowck_cache);
        let previous = config.track_state.take();
        let audit_selection = self.audit_selection.clone();
        config.track_state = Some(Box::new(move |sess| {
            if let Some(previous) = previous {
                previous(sess);
            }
            // Cargo must rebuild this selected crate when the requested
            // execution graph changes, even if its Rust source is unchanged.
            // Library dependencies delegated to ordinary rustc do not record
            // these inputs, so their checked artifacts can be shared.
            for key in ["RUST_INTERP_ENTRY", "RUST_INTERP_ENTRIES", "RUST_INTERP_LIST_TESTS", "RUST_INTERP_TEST_FILTER", "RUST_INTERP_AUDIT_SELECTION", "RUST_INTERP_RETAIN_AUDIT_BODIES", "RUST_INTERP_EXPORT_TEST", "RUST_INTERP_INLINE_LEAVES", "RUST_INTERP_TRAP_UNSUPPORTED_CALLS", "RUST_INTERP_RUN_TRY_CALLBACKS", "RUST_INTERP_ALLOCATION_TRACE", "RUST_INTERP_FUNCTION_COSTS", "RUST_INTERP_FUNCTION_DEPENDENCIES", "RUST_INTERP_BINDING_REPLAY", "RUST_INTERP_FUNCTION_CACHE", "RUST_INTERP_REPLAY_COSTS", "RUST_INTERP_REUSE_MISSES"] {
                sess.env_depinfo.borrow_mut().insert((
                    rustc_span::Symbol::intern(key),
                    std::env::var(key).ok().as_deref().map(rustc_span::Symbol::intern),
                ));
            }
            if let Some(path) = &audit_selection {
                sess.file_depinfo.borrow_mut().insert(rustc_span::Symbol::intern(&path.to_string_lossy()));
            }
        }));
    }
    fn after_crate_root_parsing(
        &mut self,
        compiler: &interface::Compiler,
        krate: &mut rustc_ast::Crate,
    ) -> Compilation {
        if !self.demand_cache {
            return Compilation::Continue;
        }
        // Own the compiler-context lifecycle so a bytecode-only compilation
        // can commit semantic queries without producing fake Cargo metadata.
        let (hash, session) =
            rustc_interface::create_and_enter_global_ctxt(compiler, krate.clone(), |tcx| {
                let _ = tcx.resolver_for_lowering();
                self.after_expansion(compiler, tcx);
                let hash = tcx
                    .sess
                    .opts
                    .incremental
                    .as_ref()
                    .map(|_| tcx.crate_hash(rustc_hir::def_id::LOCAL_CRATE));
                tcx.dep_graph.with_ignore(|| {
                    rustc_incremental::save_work_product_index(
                        tcx.sess,
                        tcx.incr_comp_session,
                        &tcx.dep_graph,
                        Default::default(),
                    )
                });
                hash
            });
        rustc_incremental::finalize_session_directory(&compiler.sess, session, hash);
        Compilation::Stop
    }
    fn after_expansion<'tcx>(&mut self, _: &interface::Compiler, tcx: TyCtxt<'tcx>) -> Compilation {
        if !self.demand {
            return Compilation::Continue;
        }
        // Experimental partial checking. Keep global type/impl consistency;
        // the lowerer checks each selected local body before asking for its MIR.
        let _ = tcx.ensure_result().check_type_wf(());
        for &id in tcx.all_local_trait_impls(()).keys() {
            let _ = tcx.ensure_result().coherent_trait(id);
        }
        let _ = tcx.ensure_result().crate_inherent_impls_validity_check(());
        let _ = tcx.ensure_result().crate_inherent_impls_overlap_check(());
        tcx.dcx().abort_if_errors();
        self.emit(tcx)
    }
    fn after_analysis<'tcx>(&mut self, _: &interface::Compiler, tcx: TyCtxt<'tcx>) -> Compilation {
        self.emit(tcx)
    }
}

fn allocation_trace_path(output: &Path) -> PathBuf {
    let mut path = output.as_os_str().to_owned();
    path.push(".allocations.jsonl");
    PathBuf::from(path)
}

fn main() -> std::process::ExitCode {
    let mut args: Vec<String> = std::env::args().collect();
    if args.len() == 2 && args[1] == "--rust-interp-capabilities" {
        println!("{}", serde_json::json!({"schema_version":1,"bytecode_version":rust_interp_bytecode::VERSION,
            "frontend_workers":serde_json::from_str::<serde_json::Value>(&wrapper_route::frontend_worker_capability()).expect("frontend worker capability"),
            "export_options":["inline-leaves","trap-unsupported-calls","run-try-callbacks","allocation-trace","entry-catalog","list-tests","filtered-tests","function-cache-reuse","function-cache-auto","borrowck-cache","frontend-workers-v1"]}));
        return std::process::ExitCode::SUCCESS;
    }
    let environment = wrapper_route::Environment::read();
    let route = wrapper_route::route(args, &environment).unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(2);
    });
    let use_driver = route.requires_exporter();
    let borrowck_mode = route.borrowck_cache;
    args = route.args;
    let wrapper = route.wrapper;
    let wants_test = environment.export_test;
    if !route.export {
        if use_driver {
            let expected = Path::new(env!("RUST_INTERP_SYSROOT")).join("bin/rustc").canonicalize();
            let supplied = Path::new(&args[0]).canonicalize();
            if !matches!((&expected, &supplied), (Ok(a), Ok(b)) if a == b) {
                eprintln!("borrowck cache requires the pinned toolchain's rustc executable");
                std::process::exit(2);
            }
            if !args.iter().any(|arg| arg == "--sysroot" || arg.starts_with("--sysroot=")) {
                args.extend(["--sysroot".into(), env!("RUST_INTERP_SYSROOT").into()]);
            }
            return native_driver::run(&args, borrowck_mode);
        }
        let status = std::process::Command::new(&args[0])
            .args(&args[1..])
            .status()
            .expect("start rustc");
        std::process::exit(status.code().unwrap_or(1));
    }
    let audit_selection = std::env::var_os("RUST_INTERP_AUDIT_SELECTION").map(PathBuf::from);
    let list_tests = match std::env::var_os("RUST_INTERP_LIST_TESTS") {
        None => false,
        Some(value) if value == "1" => true,
        Some(_) => { eprintln!("RUST_INTERP_LIST_TESTS must be 1 when set"); std::process::exit(2); }
    };
    let test_filter = std::env::var_os("RUST_INTERP_TEST_FILTER").map(|value| {
        value.to_str().ok_or("test filter must be UTF-8".into()).and_then(test_metadata::Filter::parse)
            .unwrap_or_else(|error: String| { eprintln!("{error}"); std::process::exit(2); })
    });
    if test_filter.is_some() && (list_tests || !wants_test || audit_selection.is_some() ||
        std::env::var_os("RUST_INTERP_ENTRY").is_some() || std::env::var_os("RUST_INTERP_ENTRIES").is_some()) {
        eprintln!("test filtering requires a test target without discovery, execution or audit entries");
        std::process::exit(2);
    }
    if list_tests && (!wants_test || audit_selection.is_some() ||
        std::env::var_os("RUST_INTERP_ENTRY").is_some() || std::env::var_os("RUST_INTERP_ENTRIES").is_some()) {
        eprintln!("test discovery requires a test target without execution or audit entries");
        std::process::exit(2);
    }
    let entries = if list_tests || test_filter.is_some() { vec![] } else if let Some(path) = &audit_selection {
        if std::env::var_os("RUST_INTERP_ENTRY").is_some() || std::env::var_os("RUST_INTERP_ENTRIES").is_some() {
            eprintln!("audit selection cannot be combined with execution entries");
            std::process::exit(2);
        }
        audit::read_entries(path).unwrap_or_else(|error| {
            eprintln!("invalid audit selection: {error}"); std::process::exit(2);
        })
    } else { match std::env::var("RUST_INTERP_ENTRIES") {
        Ok(value) => match serde_json::from_str::<Vec<String>>(&value) {
            Ok(entries) => entries,
            Err(error) => {
                eprintln!("RUST_INTERP_ENTRIES must be a JSON array of entry names: {error}");
                std::process::exit(2);
            }
        },
        Err(_) => vec![std::env::var("RUST_INTERP_ENTRY")
            .unwrap_or_else(|_| "rust_interp_entry".into())],
    }};
    if !args
        .iter()
        .any(|a| a == "--sysroot" || a.starts_with("--sysroot="))
    {
        args.extend(["--sysroot".into(), env!("RUST_INTERP_SYSROOT").into()]);
    }
    let output = PathBuf::from(
        std::env::var_os("RUST_INTERP_OUTPUT").expect("RUST_INTERP_OUTPUT is required"),
    );
    // A failed source revision or configuration must not leave this standalone
    // output looking like the result of the failed request.
    let old_trace = allocation_trace_path(&output);
    for path in [&output, &old_trace] {
        if let Err(e) = std::fs::remove_file(path) {
            if e.kind() != std::io::ErrorKind::NotFound {
                eprintln!("cannot remove old export output: {e}");
                std::process::exit(2);
            }
        }
    }
    let retain_audit_bodies = match std::env::var_os("RUST_INTERP_RETAIN_AUDIT_BODIES") {
        None => false,
        Some(value) if value == "1" => true,
        Some(_) => {
            eprintln!("RUST_INTERP_RETAIN_AUDIT_BODIES must be 1 when set");
            std::process::exit(2);
        }
    };
    if retain_audit_bodies && (audit_selection.is_none() || !wants_test) {
        eprintln!("retaining audit bodies requires an audit selection and a test target");
        std::process::exit(2);
    }
    let inline_leaves = match std::env::var_os("RUST_INTERP_INLINE_LEAVES") {
        None => false,
        Some(value) if value == "1" => true,
        Some(_) => {
            eprintln!("RUST_INTERP_INLINE_LEAVES must be 1 when set");
            std::process::exit(2);
        }
    };
    let trap_unsupported_calls = match std::env::var_os("RUST_INTERP_TRAP_UNSUPPORTED_CALLS") {
        None => false,
        Some(value) if value == "1" => true,
        Some(_) => {
            eprintln!("RUST_INTERP_TRAP_UNSUPPORTED_CALLS must be 1 when set");
            std::process::exit(2);
        }
    };
    let run_try_callbacks = match std::env::var_os("RUST_INTERP_RUN_TRY_CALLBACKS") {
        None => false,
        Some(value) if value == "1" => true,
        Some(_) => {
            eprintln!("RUST_INTERP_RUN_TRY_CALLBACKS must be 1 when set");
            std::process::exit(2);
        }
    };
    if run_try_callbacks && !trap_unsupported_calls {
        eprintln!("running try callbacks requires explicit unavailable-call trapping; unwinding remains unsupported");
        std::process::exit(2);
    }
    let demand = std::env::var("RUST_INTERP_DEMAND_BODIES").is_ok_and(|s| s == "1");
    if demand && borrowck_mode != wrapper_route::BorrowckCacheMode::Off {
        eprintln!("borrowck cache requires ordinary strict compiler analysis");
        std::process::exit(2);
    }
    let function_costs = function_costs::enabled().unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(2);
    });
    if function_costs && (demand || audit_selection.is_some()) {
        eprintln!("function costs require strict checking of one selected execution graph");
        std::process::exit(2);
    }
    let function_cache = function_cache::mode().unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(2);
    });
    let actual_reuse = matches!(function_cache, function_cache::Mode::Reuse | function_cache::Mode::Auto);
    let function_dependencies = function_dependencies::enabled().unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(2);
    });
    if function_dependencies && !function_costs && !actual_reuse {
        eprintln!("function dependency observation requires function costs and strict checking");
        std::process::exit(2);
    }
    let binding_replay = lower::reuse::enabled().unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(2);
    });
    if binding_replay && (!function_costs || audit_selection.is_some() || demand) {
        eprintln!("binding replay requires function costs and strict execution-graph checking");
        std::process::exit(2);
    }
    if function_cache == function_cache::Mode::Verify && (!binding_replay || !function_dependencies) {
        eprintln!("function cache verification requires binding replay and dependency observation");
        std::process::exit(2);
    }
    if actual_reuse && (demand || audit_selection.is_some() || function_costs || binding_replay) {
        eprintln!("function cache reuse requires strict checking and disabled function-cost/binding observers");
        std::process::exit(2);
    }
    let allocation_trace = match std::env::var_os("RUST_INTERP_ALLOCATION_TRACE") {
        None => false,
        Some(value) if value == "1" => true,
        Some(_) => {
            eprintln!("RUST_INTERP_ALLOCATION_TRACE must be 1 when set");
            std::process::exit(2);
        }
    };
    if allocation_trace {
        if demand || audit_selection.is_some() {
            eprintln!("allocation tracing requires strict checking of one selected execution graph");
            std::process::exit(2);
        }
    }
    if trap_unsupported_calls && demand {
        eprintln!("unavailable-call reachability requires ordinary strict frontend checking");
        std::process::exit(2);
    }
    let demand_cache = demand && std::env::var("RUST_INTERP_DEMAND_CACHE").is_ok_and(|s| s == "1");
    if list_tests && (demand || retain_audit_bodies || inline_leaves || trap_unsupported_calls ||
        allocation_trace || function_costs || function_dependencies || binding_replay ||
        function_cache != function_cache::Mode::Off) {
        eprintln!("test discovery requires strict checking without execution-graph options");
        std::process::exit(2);
    }
    if test_filter.is_some() && demand {
        eprintln!("test filtering requires ordinary strict frontend checking");
        std::process::exit(2);
    }
    if audit_selection.is_some() && demand {
        eprintln!("lowering audits require ordinary strict frontend checking");
        std::process::exit(2);
    }
    if wrapper && demand {
        eprintln!("demand checking is a standalone experiment; it does not produce Cargo metadata");
        std::process::exit(2);
    }
    if let Some(capture) = std::env::var_os("RUST_INTERP_CAPTURE") {
        let environment: std::collections::BTreeMap<_, _> = std::env::vars()
            .filter(|(k, _)| {
                k.starts_with("CARGO_PKG_")
                    || k.starts_with("CARGO_FEATURE_")
                    || k.starts_with("CARGO_CFG_")
                    || [
                        "OUT_DIR",
                        "CARGO_MANIFEST_DIR",
                        "CARGO_MANIFEST_PATH",
                        "CARGO_CRATE_NAME",
                        "CARGO_PRIMARY_PACKAGE",
                        "CARGO_BIN_NAME",
                    ]
                    .contains(&k.as_str())
            })
            .collect();
        let record = serde_json::json!({"args":args,"cwd":std::env::current_dir().expect("compiler cwd"),"env":environment});
        std::fs::write(
            capture,
            serde_json::to_vec_pretty(&record).expect("serialize invocation"),
        )
        .expect("save compiler invocation");
    }
    // Refuse codegen: the application path must never silently use LLVM.
    let mut emissions = Vec::new();
    for (i, arg) in args.iter().enumerate() {
        let value = arg.strip_prefix("--emit=").or_else(|| {
            (arg == "--emit")
                .then(|| args.get(i + 1).map(String::as_str))
                .flatten()
        });
        if let Some(value) = value {
            emissions.extend(
                value
                    .split(',')
                    .map(|part| part.split('=').next().unwrap_or("")),
            );
        }
    }
    if !emissions.contains(&"metadata")
        || emissions
            .iter()
            .any(|kind| !["metadata", "dep-info"].contains(kind))
    {
        eprintln!("rust-interp-export requires --emit=metadata (use cargo check)");
        std::process::exit(2);
    }
    let mut callbacks = Export {
        entries,
        output,
        started: Instant::now(),
        demand,
        demand_cache,
        audit_selection,
        list_tests,
        test_filter,
        retain_audit_bodies,
        test_body: wants_test,
        inline_leaves,
        trap_unsupported_calls,
        run_try_callbacks,
        allocation_trace,
        borrowck_cache: borrowck_mode,
    };
    let result = rustc_driver::catch_fatal_errors(|| rustc_driver::run_compiler(&args, &mut callbacks));
    borrowck_cache::report();
    if result.is_err() { std::process::ExitCode::FAILURE } else { std::process::ExitCode::SUCCESS }
}
