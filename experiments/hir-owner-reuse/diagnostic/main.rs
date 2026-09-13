#![feature(rustc_private)]
extern crate rustc_ast;
extern crate rustc_data_structures;
extern crate rustc_driver;
extern crate rustc_hir;
extern crate rustc_interface;
extern crate rustc_macros;
extern crate rustc_middle;
extern crate rustc_serialize;
extern crate rustc_session;
extern crate rustc_span;

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::fs::OpenOptions;
use std::hash::Hasher;
use std::io::Write as _;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use rustc_ast as ast;
use rustc_ast::node_id::NodeSet;
use rustc_ast::visit::{self, Visitor};
use rustc_data_structures::fingerprint::Fingerprint;
use rustc_data_structures::stable_hash::StableHasher;
use rustc_data_structures::profiling::{TimePassesFormat, get_resident_set_size, print_time_passes_entry};
use rustc_driver::{Callbacks, Compilation, TimePassesCallbacks};
use rustc_interface::interface;
use rustc_middle::middle::resolve::ResolverAstLowering;
use rustc_middle::ty::TyCtxt;
use rustc_serialize::Encodable;
use rustc_serialize::opaque::mem_encoder::MemEncoder;
use rustc_span::def_id::LOCAL_CRATE;

// Authoritative gate is the identical source in the actual compiler candidate.
#[path = "../candidate/owner_cache/input.rs"]
mod input;
#[path = "generated/input_instrumented.rs"]
mod instrumented;
#[path = "generated/binding.rs"]
mod binding;

const _: () = {
    let actual = include_bytes!("../candidate/owner_cache/input.rs");
    let frozen = include_bytes!("generated/gate.snapshot");
    assert!(actual.len() == frozen.len(), "regenerate the exact gate binding");
    let mut i = 0;
    while i < actual.len() {
        assert!(actual[i] == frozen[i], "gate differs from the generated diagnostic");
        i += 1;
    }
};

fn json(value: &str) -> String {
    let mut output = String::from("\"");
    for ch in value.chars() {
        match ch {
            '"' => output.push_str("\\\""), '\\' => output.push_str("\\\\"),
            '\n' => output.push_str("\\n"), '\r' => output.push_str("\\r"), '\t' => output.push_str("\\t"),
            ch if ch < '\u{20}' => { write!(&mut output, "\\u{:04x}", ch as u32).unwrap(); }
            ch => output.push(ch),
        }
    }
    output.push('"');
    output
}
fn hex(value: Fingerprint) -> String {
    let (a, b) = value.split();
    format!("{:016x}{:016x}", a.as_u64(), b.as_u64())
}
fn codec_identity() -> String {
    let source = concat!(include_str!("../candidate/owner_cache/mod.rs"),
        include_str!("../candidate/owner_cache/input.rs"), include_str!("../candidate/owner_cache/wire.rs"),
        include_str!("../candidate/owner_cache/validate.rs"), include_str!("../candidate/owner_cache/capture.rs"),
        include_str!("../candidate/owner_cache/materialize.rs"));
    let mut h = StableHasher::new();
    h.write(source.as_bytes());
    hex(h.finish())
}
fn encoded<T: Encodable<MemEncoder>>(value: &T) -> Vec<u8> {
    let mut encoder = MemEncoder::new();
    value.encode(&mut encoder);
    encoder.finish()
}
fn key_bytes(tcx: TyCtxt<'_>, codec: &str, value: &input::ResolvedInput) -> usize {
    let mut encoder = MemEncoder::new();
    "hir-owner-reuse-v1".encode(&mut encoder);
    codec.encode(&mut encoder);
    tcx.sess.cfg_version.encode(&mut encoder);
    tcx.sess.opts.dep_tracking_hash(false).as_u64().encode(&mut encoder);
    value.encode(&mut encoder);
    encoder.finish().len()
}

#[derive(Default)]
struct Count { owners: usize, input_eligible: usize, key_budget_eligible: usize,
    total_input_item_span_bytes: usize, source_bytes: usize, input_bytes: usize, key_bytes: usize }
#[derive(Default)]
struct Report {
    counts: BTreeMap<String, Count>, reasons: BTreeMap<String, usize>, rows: Vec<String>,
    problems: Vec<String>, resolver_owners: usize, unvisited_resolver_owners: usize,
    incremental: bool, errors_before_walk: bool, version_override: bool, crate_name: String, cfg_version: String,
}
struct Walk<'a, 'tcx> {
    tcx: TyCtxt<'tcx>, resolver: &'a ResolverAstLowering<'tcx>, report: Report,
    seen: NodeSet, codec: String,
}
impl Walk<'_, '_> {
    fn owner(&mut self, id: ast::NodeId, kind: &str, item: Option<&ast::Item>) {
        if !self.seen.insert(id) { self.report.problems.push(format!("duplicate owner {id:?}")); return; }
        let Some(owner) = self.resolver.owners.get(&id) else {
            self.report.problems.push(format!("visited owner absent from resolver {id:?}")); return;
        };
        let identity = hex(self.tcx.def_path_hash(owner.def_id.to_def_id()).0);
        let name = item.and_then(|item| match &item.kind {
            ast::ItemKind::Fn(function) => Some(function.ident.name.as_str()), _ => None,
        }).unwrap_or("");
        let count = self.report.counts.entry(kind.to_owned()).or_default();
        count.owners += 1;
        if let Some(item) = item { count.total_input_item_span_bytes += (item.span.hi() - item.span.lo()).0 as usize; }
        let mut reason = "hook-does-not-accept-this-owner-category".to_owned();
        let mut eligible = false;
        let mut key_budget = false;
        let (mut source_bytes, mut input_bytes, mut key_size) = (0, 0, 0);
        if let Some(item) = item {
            let exact = input::probe(self.tcx, self.resolver, item);
            instrumented::diagnostic_reset();
            let diagnostic = instrumented::probe(self.tcx, self.resolver, item);
            match (&exact, &diagnostic) {
                (Some(exact), Some(diagnostic)) if encoded(&exact.input) == encoded(&diagnostic.input)
                    && exact.current_owner == diagnostic.current_owner && exact.current_span == diagnostic.current_span => {}
                (None, None) if instrumented::diagnostic_reason().is_some() => {}
                _ => self.report.problems.push(format!("gate/instrumentation disagreement for {identity}")),
            }
            if let Some(probe) = exact {
                eligible = true;
                source_bytes = probe.input.source.len();
                input_bytes = encoded(&probe.input).len();
                key_size = key_bytes(self.tcx, &self.codec, &probe.input);
                key_budget = key_size <= 512 * 1024;
                reason = if key_budget { "input-gate-accepted-output-capture-unmeasured" }
                         else { "encoded-key-exceeds-candidate-budget" }.to_owned();
                count.input_eligible += 1;
                count.key_budget_eligible += usize::from(key_budget);
                count.source_bytes += source_bytes;
                count.input_bytes += input_bytes;
                count.key_bytes += key_size;
            } else {
                reason = match instrumented::diagnostic_reason() {
                    Some(line) => format!("gate-input.rs:{line}"), None => "missing-rejection-site".to_owned(),
                };
            }
        }
        *self.report.reasons.entry(reason.clone()).or_default() += 1;
        self.report.rows.push(format!(
            "{{\"owner_def_path_hash\":{},\"owner_name\":{},\"kind\":{},\"input_eligible\":{eligible},\"key_budget_eligible\":{key_budget},\"reason\":{},\"source_bytes\":{source_bytes},\"encoded_input_bytes\":{input_bytes},\"encoded_candidate_key_bytes\":{key_size}}}",
            json(&identity), json(name), json(kind), json(&reason)));
    }
}
impl<'ast> Visitor<'ast> for Walk<'_, '_> {
    fn visit_crate(&mut self, krate: &'ast ast::Crate) {
        self.owner(ast::CRATE_NODE_ID, "crate", None);
        visit::walk_crate(self, krate);
    }
    fn visit_item(&mut self, item: &'ast ast::Item) {
        self.owner(item.id, item.kind.descr(), Some(item));
        visit::walk_item(self, item);
    }
    fn visit_assoc_item(&mut self, item: &'ast ast::AssocItem, ctxt: visit::AssocCtxt) {
        let kind = match ctxt { visit::AssocCtxt::Trait => "trait-item", visit::AssocCtxt::Impl { .. } => "impl-item" };
        self.owner(item.id, kind, None);
        visit::walk_assoc_item(self, item, ctxt);
    }
    fn visit_foreign_item(&mut self, item: &'ast ast::ForeignItem) {
        self.owner(item.id, "foreign-item", None);
        visit::walk_item(self, item);
    }
    fn visit_nested_use_tree(&mut self, tree: &'ast ast::UseTree, id: ast::NodeId) {
        self.owner(id, "nested-use-tree", None);
        self.visit_use_tree(tree);
    }
    fn visit_attribute(&mut self, _: &'ast ast::Attribute) {
        // Matches index_ast's explicit omission of expressions inside attributes.
    }
}

#[derive(Default)]
struct Diagnostic { standard: TimePassesCallbacks, time_passes: Option<TimePassesFormat>,
    report: Option<Report>, after_analysis: bool, effective_sysroot: String }
impl Callbacks for Diagnostic {
    fn config(&mut self, config: &mut interface::Config) {
        self.standard.config(config); // Includes native rustc's trimmed diagnostic paths.
        self.time_passes = (config.opts.prints.is_empty() && config.opts.unstable_opts.time_passes)
            .then_some(config.opts.unstable_opts.time_passes_format);
        // A relocated driver executable must use the same default as its linked
        // stock compiler. Explicit --sysroot and every other caller option survive.
        config.opts.sysroot.default = PathBuf::from(env!("HIR_COVERAGE_PUBLIC_SYSROOT"));
        self.effective_sysroot = config.opts.sysroot.path().display().to_string();
    }
    fn after_expansion<'tcx>(&mut self, _: &interface::Compiler, tcx: TyCtxt<'tcx>) -> Compilation {
        // Do not force HIR, early-lint, analysis or codegen queries here. Stock
        // driver/index_ast ordering remains intact. A report is usable only after
        // subsequent normal analysis and successful compiler completion.
        let crate_name = tcx.crate_name(LOCAL_CRATE).to_string();
        let report = {
            let (resolver, krate) = tcx.resolver_for_lowering();
            let resolver = resolver.borrow();
            let krate = krate.borrow();
            let mut walk = Walk { tcx, resolver: &resolver, seen: NodeSet::default(), codec: codec_identity(),
                report: Report { incremental: tcx.incr_comp_session.is_some(),
                    errors_before_walk: tcx.dcx().has_errors().is_some(),
                    version_override: std::env::var_os("RUSTC_FORCE_RUSTC_VERSION").is_some(), resolver_owners: resolver.owners.len(),
                    crate_name, cfg_version: tcx.sess.cfg_version.to_owned(),
                    ..Report::default() } };
            walk.visit_crate(&krate);
            walk.report.unvisited_resolver_owners = resolver.owners.keys().filter(|id| !walk.seen.contains(id)).count();
            walk.report
        }; // Visitor and both Steal borrow guards are dropped before stock lowering.
        self.report = Some(report);
        Compilation::Continue
    }
    fn after_analysis<'tcx>(&mut self, _: &interface::Compiler, _: TyCtxt<'tcx>) -> Compilation {
        self.after_analysis = true;
        Compilation::Continue
    }
}
impl Diagnostic {
    fn output(&self, args: &[String], start: u128, compiler_ok: bool) -> String {
        let report = self.report.as_ref();
        let usable = compiler_ok && self.after_analysis && report.is_some_and(|r| !r.errors_before_walk && !r.version_override
            && r.unvisited_resolver_owners == 0 && r.problems.is_empty());
        let counts = report.map(|r| r.counts.iter().map(|(kind, c)| format!(
            "{}:{{\"owners\":{},\"input_eligible\":{},\"key_budget_eligible\":{},\"total_input_item_span_bytes\":{},\"eligible_source_bytes\":{},\"encoded_input_bytes\":{},\"encoded_candidate_key_bytes\":{}}}",
            json(kind), c.owners, c.input_eligible, c.key_budget_eligible, c.total_input_item_span_bytes, c.source_bytes, c.input_bytes, c.key_bytes
        )).collect::<Vec<_>>().join(",")).unwrap_or_default();
        let reasons = report.map(|r| r.reasons.iter().map(|(reason, count)| format!("{}:{count}", json(reason)))
            .collect::<Vec<_>>().join(",")).unwrap_or_default();
        let rows = report.map(|r| r.rows.join(",")).unwrap_or_default();
        let problems = report.map(|r| r.problems.iter().map(|s| json(s)).collect::<Vec<_>>().join(",")).unwrap_or_default();
        format!(concat!("{{\"policy\":\"hir-owner-input-coverage-v1\",\"benchmark\":false,\"cache_hits_measured\":false,",
            "\"pid\":{},\"started_unix_ns\":{},\"compiler_commit\":{},\"gate_sha256\":{},\"candidate_patch_sha256\":{},",
            "\"ordinary_compiler_succeeded\":{},\"coverage_usable\":{},\"after_expansion_seen\":{},\"after_analysis_seen\":{},",
            "\"effective_sysroot\":{},\"crate_name\":{},\"cfg_version\":{},\"incremental_session\":{},\"errors_before_walk\":{},\"version_override_present\":{},",
            "\"resolver_owners\":{},\"unvisited_resolver_owners\":{},\"compiler_argv\":[{}],",
            "\"counts\":{{{}}},\"reasons\":{{{}}},\"problems\":[{}],\"owners\":[{}]}}\n"),
            std::process::id(), start, json(binding::PUBLIC_COMMIT), json(binding::GATE_SHA256), json(binding::PATCH_SHA256),
            compiler_ok, usable, report.is_some(), self.after_analysis, json(&self.effective_sysroot),
            json(report.map_or("", |r| &r.crate_name)), json(report.map_or("", |r| &r.cfg_version)),
            report.is_some_and(|r| r.incremental), report.is_some_and(|r| r.errors_before_walk),
            report.is_some_and(|r| r.version_override),
            report.map_or(0, |r| r.resolver_owners), report.map_or(0, |r| r.unvisited_resolver_owners),
            args.iter().map(|s| json(s)).collect::<Vec<_>>().join(","), counts, reasons, problems, rows)
    }
}
fn main() -> ExitCode {
    let started = Instant::now();
    let start_rss = get_resident_set_size();
    let start = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    let early = rustc_session::EarlyDiagCtxt::new(rustc_session::config::ErrorOutputType::default());
    rustc_driver::init_rustc_env_logger(&early);
    rustc_driver::install_ice_hook(rustc_driver::DEFAULT_BUG_REPORT_URL, |_| ());
    rustc_driver::install_ctrlc_handler();
    let linked_version = rustc_interface::util::rustc_version_str().unwrap_or("");
    // The full binary/compiler identity is an external build-admission receipt.
    // This additional linked-library check rejects the existing custom compiler.
    if !linked_version.contains("(cea272fa3 ") {
        eprintln!("HIR coverage requires the reviewed public compiler, linked version: {linked_version}");
        return ExitCode::from(2);
    }
    let mut args = rustc_driver::args::raw_args(&early);
    // Cargo supplies its compiler executable before the ordinary compiler argv.
    // Explicit wrapper mode rejects a different compiler; it starts no subprocess.
    if std::env::var_os("HIR_OWNER_COVERAGE_WRAPPER").is_some() {
        if args.get(1).map(String::as_str) != Some(env!("HIR_COVERAGE_PUBLIC_RUSTC")) {
            eprintln!("HIR coverage wrapper requires the exact build-bound public rustc path");
            return ExitCode::from(2);
        }
        args.remove(1);
    }
    let Some(directory) = std::env::var_os("HIR_OWNER_COVERAGE_OUTPUT") else {
        eprintln!("HIR_OWNER_COVERAGE_OUTPUT must name an existing owned output directory");
        return ExitCode::from(2);
    };
    let directory = PathBuf::from(directory);
    if !directory.is_dir() { eprintln!("HIR coverage output directory is absent"); return ExitCode::from(2); }
    let mut diagnostic = Diagnostic::default();
    let result = rustc_driver::catch_fatal_errors(|| rustc_driver::run_compiler(&args, &mut diagnostic));
    if let Some(format) = diagnostic.time_passes {
        print_time_passes_entry("total", started.elapsed(), start_rss, get_resident_set_size(), format);
    }
    let compiler_ok = result.is_ok();
    let output = diagnostic.output(&args, start, compiler_ok);
    let path = directory.join(format!("hir-owner-coverage-{}-{start}.json", std::process::id()));
    let retained = OpenOptions::new().write(true).create_new(true).open(&path)
        .and_then(|mut file| file.write_all(output.as_bytes()));
    if let Err(error) = retained { eprintln!("cannot retain HIR coverage report {}: {error}", path.display()); return ExitCode::from(2); }
    if diagnostic.report.as_ref().is_some_and(|r| !r.problems.is_empty()) {
        eprintln!("HIR coverage report is invalid; normal compiler completion was retained");
        return ExitCode::from(2);
    }
    if compiler_ok { ExitCode::SUCCESS } else { ExitCode::FAILURE }
}
