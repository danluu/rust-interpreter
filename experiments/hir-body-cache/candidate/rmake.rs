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
    assert!(diagnostics.contains("cache_hits=0 body_codec=1 materializer=0"), "{diagnostics}");
    for name in ["add", "field", "method", "double", "selected", "shadow", "generic",
        "conditional", "array_index", "uninitialized", "raw", "arithmetic", "literals", "unsafe_block"] {
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
}
