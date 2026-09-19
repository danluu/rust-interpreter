//@ ignore-cross-compile

// Unrun capture and separately selected reuse controls. Capture comparisons
// remain stock lowering. Reuse hits must pass the built-in tree/journal/state
// verifier as well as these ordinary native behavior/diagnostic controls.
use std::path::{Path, PathBuf};
use run_make_support::{Rustc, rfs, run, rustc};

fn compiler(enabled: bool, info: bool) -> Rustc {
    compiler_options(enabled, false, info, if enabled { "cache-on" } else { "cache-off" })
}
fn compiler_options(enabled: bool, reuse: bool, info: bool, incremental: &str) -> Rustc {
    let mut command = rustc();
    // Bootstrap supplies this to compiletest. Normal histories must use the
    // real compiler version; production prepare correctly rejects any override.
    command.env_remove("RUSTC_FORCE_RUSTC_VERSION");
    command.input("input.rs").crate_name("body_journal_test").output("body_journal_test")
        .metadata("body_journal_test").incremental(incremental)
        .arg(format!("-Zhir-body-cache-capture={enabled}"))
        .arg("-Cdebuginfo=2").arg("--edition=2024");
    if reuse { command.arg("-Zhir-body-cache-reuse=true"); }
    if info { command.arg("-Zincremental-info"); }
    command
}

fn success(source: &str, repeated_anchor: bool) {
    rfs::write("input.rs", source);
    compiler(false, false).run();
    let ordinary = run("body_journal_test").stdout_utf8();
    let diagnostics = compiler(true, true).run().stderr_utf8();
    assert_eq!(ordinary, run("body_journal_test").stdout_utf8());
    let mode = if repeated_anchor { "same-tree-and-journal-after-stock-lowering" } else { "cold-tree-and-journal-after-stock-lowering" };
    assert!(diagnostics.contains(&format!("[hir-body-capture] anchor {mode}")), "{diagnostics}");
    assert!(diagnostics.contains("cache_hits=0 body_codec=1 prepared_values=1 cold_materialization_audit=1 hit_materializer=0"), "{diagnostics}");
    for name in ["add", "field", "method", "double", "selected", "shadow", "generic",
        "conditional", "array_index", "uninitialized", "raw", "arithmetic", "literals", "unsafe_block", "flow", "early"] {
        assert!(["cold-tree-and-journal-after-stock-lowering", "same-tree-and-journal-after-stock-lowering",
            "changed-tree-or-journal-after-stock-lowering"].iter().any(|state|
                diagnostics.contains(&format!("[hir-body-capture] {name} {state}"))), "{diagnostics}");
    }
}

// Discover policy-specific packs; corruption still reaches the actual stored
// records. A truncated pack must cause ordinary cold lowering, never a hit.
fn records(root: &Path, prefix: &str, output: &mut Vec<PathBuf>) {
    for entry in std::fs::read_dir(root).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() { records(&path, prefix, output); }
        else if path.file_name().unwrap().to_string_lossy().starts_with(prefix)
            && path.extension().is_some_and(|ext| ext == "pack") { output.push(path); }
    }
}

fn reuse_compiler(info: bool) -> Rustc {
    compiler_options(false, true, info, "cache-reuse")
}
fn expect_reuse(info: &str, name: &str, hit: bool) {
    expect_reuse_count(info, name, hit, 1);
}
fn expect_reuse_count(info: &str, name: &str, hit: bool, count: usize) {
    let expected = if hit {
        format!("[hir-body-reuse] {name} hit cache_hits=1 verify_tree=1 verify_journal=1 verify_poststate=1")
    } else {
        format!("[hir-body-capture] {name} cold-tree-and-journal-after-stock-lowering")
    };
    assert_eq!(info.matches(&expected).count(), count, "expected {count} copies of {expected}\n{info}");
}
fn reuse_success(source: &str, hit: bool) -> String {
    rfs::write("input.rs", source);
    compiler(false, false).run();
    let ordinary = run("body_journal_test").stdout_utf8();
    let info = reuse_compiler(true).run().stderr_utf8();
    assert_eq!(ordinary, run("body_journal_test").stdout_utf8());
    for name in ["anchor", "add", "method", "double", "shadow", "generic",
        "conditional", "array_index", "uninitialized", "raw", "arithmetic", "literals", "unsafe_block", "flow", "early"] {
        expect_reuse(&info, name, hit);
    }
    // Distinguish inherent field from the DefaultBody trait implementation,
    // and require both Left/Right trait-implementation choose bodies.
    expect_reuse_count(&info, "field", hit, 2);
    expect_reuse_count(&info, "choose", hit, 2);
    info
}
fn reuse_raw_control(source: &str, flags: &[&str], error: Option<&str>) {
    rfs::write("input.rs", source);
    let compile = |mut command: Rustc| {
        command.arg("--error-format=json");
        for flag in flags { command.arg(flag); }
        if error.is_some() { command.run_fail().stderr_utf8() } else { command.run().stderr_utf8() }
    };
    let ordinary = compile(compiler(false, false));
    let candidate = compile(reuse_compiler(false));
    assert_eq!(ordinary, candidate);
    if let Some(code) = error { assert!(candidate.contains(code), "{candidate}"); }
    else { run("body_journal_test"); }
}
fn reuse_info(source: &str, flags: &[&str], fails: bool) -> String {
    rfs::write("input.rs", source);
    let mut command = reuse_compiler(true);
    for flag in flags { command.arg(flag); }
    if fails { command.run_fail().stderr_utf8() } else { command.run().stderr_utf8() }
}
fn reuse_controls(original: &str) {
    reuse_success(original, false);
    reuse_success(&original.replace("x + 3", "x + 17"), true);
    reuse_success(&original.replace("struct Counter", "// Rebase current spans: λ 🚀\nstruct Counter"), true);
    reuse_success(original, true);
    let info = reuse_success(&original.replace("Left as Selected", "Right as Selected"), true);
    expect_reuse(&info, "selected", false); // exact current trait/import input changed
    let info = reuse_success(original, true); expect_reuse(&info, "selected", false);
    // Activate real uncalled failures by source edits, keeping cfg/options
    // unchanged so the unaffected anchor can actually hit in the failing run.
    for (cfg, code) in [("type_error", "E0308"), ("borrow_error", "E0382"),
                       ("const_error", "E0080"), ("panic_error", "unconditional_panic")] {
        let source = original.replace(&format!("#[cfg({cfg})] "), "");
        reuse_raw_control(&source, &[], Some(code));
        let info = reuse_compiler(true).run_fail().stderr_utf8();
        expect_reuse(&info, "anchor", true);
        reuse_success(original, true);
    }
    let mut paths = Vec::new(); records(Path::new("cache-reuse"), "hir-body-reuse-v2-", &mut paths);
    assert!(!paths.is_empty());
    for path in paths { rfs::write(path, b"{\"truncated\":"); }
    reuse_success(&original.replace("x + 3", "x + 29"), false);
    reuse_success(original, true);
    let anchor = "fn anchor() -> u32 { 3 }\nfn main() { assert_eq!(anchor(), 3); }\n";
    reuse_raw_control(anchor, &[], None);
    for feature in ["async_fn_track_caller", "iter_next_chunk"] {
        let source = format!("#![feature({feature})]\n{anchor}");
        rfs::write("input.rs", &source);
        let info = reuse_compiler(true).run().stderr_utf8();
        expect_reuse(&info, "anchor", false);
        reuse_raw_control(&source, &[], None); reuse_raw_control(anchor, &[], None);
    }
    let body = "fn anchor() -> u32 { let unused = 1; 0 }\nfn main() { assert_eq!(anchor(), 0); }\n";
    for (index, (level, error)) in [("allow", None), ("deny", Some("unused_variables")), ("allow", None)].into_iter().enumerate() {
        let source = format!("#![{level}(unused_variables)]\n{body}");
        reuse_raw_control(&source, &[], error);
        if index > 0 {
            expect_reuse(&reuse_info(&source, &[], error.is_some()), "anchor", true);
        }
    }
    for (index, (level, error)) in [("allow", None), ("deny", Some("unused_variables")), ("allow", None)].into_iter().enumerate() {
        let source = format!("mod outer {{ #![{level}(unused_variables)]\n\
            pub(super) fn anchor() -> u32 {{ let unused = 1; 0 }} }}\n\
            fn main() {{ assert_eq!(outer::anchor(), 0); }}\n");
        reuse_raw_control(&source, &[], error);
        if index > 0 {
            expect_reuse(&reuse_info(&source, &[], error.is_some()), "anchor", true);
        }
    }
    // Command-line lint flags are tracked-key changes, unlike the current
    // crate/module lint queries above. Probe each new flag state BEFORE the
    // raw comparison populates it; no assertion about failed-session reuse.
    for (flag, error) in [("-A", None), ("-D", Some("unused_variables"))] {
        expect_reuse(&reuse_info(body, &[flag, "unused_variables"], error.is_some()), "anchor", false);
        reuse_raw_control(body, &[flag, "unused_variables"], error);
    }
    reuse_raw_control(body, &["-A", "unused_variables"], None);
    reuse_raw_control(original, &[], None);
}

// No diagnostics are filtered or rewritten. Cache-info probes are separate
// ordinary compilations so exact JSON comparisons keep their original bytes.
fn raw_control(source: &str, flags: &[&str], fails: bool) {
    rfs::write("input.rs", source);
    let compile = |enabled| {
        let mut command = compiler(enabled, false);
        command.arg("--error-format=json");
        for flag in flags { command.arg(flag); }
        if fails { command.run_fail().stderr_utf8() } else { command.run().stderr_utf8() }
    };
    let ordinary = compile(false);
    if !fails { run("body_journal_test"); }
    let candidate = compile(true);
    assert_eq!(ordinary, candidate);
    if fails { assert!(candidate.contains("unused_variables"), "{candidate}"); }
    else { run("body_journal_test"); }
}

fn entry_context_controls() {
    // Owner source stays byte-identical as language and library declarations
    // change outside it. The source path and ordinary compiler flags stay fixed.
    let anchor = "fn anchor() -> u32 { 3 }\nfn main() { assert_eq!(anchor(), 3); }\n";
    raw_control(anchor, &[], false);
    for feature in ["async_fn_track_caller", "iter_next_chunk"] {
        let source = format!("#![feature({feature})]\n{anchor}");
        rfs::write("input.rs", &source);
        // Neither new feature state has a previous matching record.
        let info = compiler(true, true).run().stderr_utf8();
        assert!(info.contains("[hir-body-capture] anchor cold-tree-and-journal-after-stock-lowering"), "{info}");
        run("body_journal_test");
        raw_control(&source, &[], false);
        raw_control(anchor, &[], false);
    }
    let body = "fn anchor() -> u32 { let unused = 1; 0 }\nfn main() { assert_eq!(anchor(), 0); }\n";
    raw_control(&format!("#![allow(unused_variables)]\n{body}"), &[], false);
    raw_control(&format!("#![deny(unused_variables)]\n{body}"), &[], true);
    raw_control(&format!("#![allow(unused_variables)]\n{body}"), &[], false);
    raw_control(body, &["-A", "unused_variables"], false);
    raw_control(body, &["-D", "unused_variables"], true);
    raw_control(body, &["-A", "unused_variables"], false);
}

fn version_override_controls(original: &str) {
    let invalid = original.replace("#[cfg(type_error)] ", "");
    assert_ne!(invalid, original);
    for (label, version) in [("empty", ""), ("nonempty", "fixture-version-override")] {
        let mut ordinary_output = None;
        let mut ordinary_diagnostics = None;
        for (mode, capture, reuse) in [("ordinary", false, false), ("capture", true, false), ("reuse", false, true)] {
            // Every mode/value/outcome has an independent fresh incremental
            // directory. These controls never populate a normal cold history.
            let positive = format!("override-{label}-{mode}-positive");
            let negative = format!("override-{label}-{mode}-negative");
            assert!(!Path::new(&positive).exists());
            assert!(!Path::new(&negative).exists());
            rfs::write("input.rs", original);
            let mut command = compiler_options(capture, reuse, true, &positive);
            // Reintroduce the explicit value AFTER common env_remove, including
            // the empty value: var_os(...).is_some() must reject both cases.
            command.env("RUSTC_FORCE_RUSTC_VERSION", version);
            let info = command.run().stderr_utf8();
            assert!(!info.contains("[hir-body-capture]") && !info.contains("[hir-body-reuse]"), "{info}");
            let output = run("body_journal_test").stdout_utf8();
            if let Some(expected) = &ordinary_output { assert_eq!(&output, expected); }
            else { ordinary_output = Some(output); }

            rfs::write("input.rs", &invalid);
            let mut command = compiler_options(capture, reuse, false, &negative);
            command.env("RUSTC_FORCE_RUSTC_VERSION", version).arg("--error-format=json");
            let diagnostics = command.run_fail().stderr_utf8();
            assert!(diagnostics.contains("E0308"), "{diagnostics}");
            assert!(!diagnostics.contains("[hir-body-capture]") && !diagnostics.contains("[hir-body-reuse]"), "{diagnostics}");
            if let Some(expected) = &ordinary_diagnostics { assert_eq!(&diagnostics, expected); }
            else { ordinary_diagnostics = Some(diagnostics); }
            for directory in [&positive, &negative] {
                let mut files = Vec::new();
                if Path::new(directory).exists() { records(Path::new(directory), "hir-body-", &mut files); }
                assert!(files.is_empty(), "version override unexpectedly wrote HIR sidecars: {files:?}");
            }
        }
    }
}

fn main() {
    let original = rfs::read_to_string("fixture.rs");
    success(&original, false);
    success(&original.replace("x + 3", "x + 17"), true);
    let moved = original.replace("struct Counter", "// Earlier source extent moves: λ 🚀\nstruct Counter");
    success(&moved, true);
    success(&original, true);
    let trait_edit = original.replace("Left as Selected", "Right as Selected");
    success(&trait_edit, true);
    success(&original, true);
    for (cfg, code) in [("type_error", "E0308"), ("borrow_error", "E0382"),
                        ("const_error", "E0080"), ("panic_error", "unconditional_panic")] {
        rfs::write("input.rs", &original);
        let ordinary = compiler(false, false).arg("--cfg").arg(cfg).arg("--error-format=json")
            .run_fail().stderr_utf8();
        let candidate = compiler(true, false).arg("--cfg").arg(cfg).arg("--error-format=json")
            .run_fail().stderr_utf8();
        assert!(ordinary.contains(code), "{ordinary}");
        assert_eq!(ordinary, candidate);
        // Changing cfg is a normal tracked-input invalidation. It must not be
        // relabeled a cold/hit test, and restoration still compiles normally.
        success(&original, true);
    }
    let mut paths = Vec::new(); records(Path::new("cache-on"), "hir-body-capture-v2-", &mut paths);
    assert!(!paths.is_empty());
    for path in paths { rfs::write(path, b"{\"truncated\":"); }
    success(&original.replace("x + 3", "x + 29"), false);
    success(&original, true);
    entry_context_controls();
    reuse_controls(&original);
    version_override_controls(&original);
    rfs::write("input.rs", &original);
    compiler(false, false).run(); compiler(true, false).run();
}
