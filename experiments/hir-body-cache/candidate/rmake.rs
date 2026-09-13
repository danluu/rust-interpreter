//@ ignore-cross-compile

// Unrun capture checkpoint controls. A repeated journal is explicitly NOT a
// cache hit: both arms always perform stock lowering and normal compilation.
use std::path::{Path, PathBuf};
use run_make_support::{Rustc, rfs, run, rustc};

fn compiler(enabled: bool, info: bool) -> Rustc {
    let mut command = rustc();
    command.input("input.rs").crate_name("body_journal_test").output("body_journal_test")
        .metadata("body_journal_test").incremental(if enabled { "cache-on" } else { "cache-off" })
        .arg(format!("-Zhir-body-cache-capture={enabled}"))
        .arg("-Cdebuginfo=2").arg("--edition=2024");
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

fn records(root: &Path, output: &mut Vec<PathBuf>) {
    for entry in std::fs::read_dir(root).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() { records(&path, output); }
        else if path.file_name().unwrap().to_string_lossy().starts_with("hir-body-capture-v2-")
            && path.extension().is_some_and(|ext| ext == "json") { output.push(path); }
    }
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
    let mut paths = Vec::new(); records(Path::new("cache-on"), &mut paths);
    assert!(!paths.is_empty());
    for path in paths { rfs::write(path, b"{\"truncated\":"); }
    success(&original.replace("x + 3", "x + 29"), false);
    success(&original, true);
    entry_context_controls();
    rfs::write("input.rs", &original);
    compiler(false, false).run(); compiler(true, false).run();
}
