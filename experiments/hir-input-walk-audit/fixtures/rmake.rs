//@ ignore-cross-compile

// This entire directory is an unrun qualification proposal. It requires the
// distinct unconditional audit compiler; its commands are forbidden for timing.
use std::path::Path;
use run_make_support::{Rustc, rfs, run, rustc};

// Preserve the existing fixture and every original run-make assertion exactly.
mod inherited {
    include!("inherited-rmake.rs");
    pub(super) fn run_all() { main(); }
}

fn compiler(label: &str, mode: &str, info: bool) -> Rustc {
    let directory = format!("audit-{label}-{mode}-{}", if info { "info" } else { "raw" });
    assert!(!Path::new(&directory).exists(), "coverage requires an untouched incremental directory");
    let mut command = rustc();
    command.env_remove("RUSTC_FORCE_RUSTC_VERSION");
    command.input("input.rs").crate_name("input_walk_audit").output("input_walk_audit")
        .metadata("input_walk_audit").incremental(&directory)
        .arg("--edition=2024").arg("-Cdebuginfo=2")
        .arg(format!("-Zhir-body-cache-capture={}", mode == "capture"))
        .arg(format!("-Zhir-body-cache-reuse={}", mode == "reuse"));
    if info { command.arg("-Zincremental-info"); }
    else { command.arg("--error-format=json"); }
    command
}

fn raw_control(label: &str, source: &str, error: Option<&str>) {
    rfs::write("input.rs", source);
    let mut diagnostics = None;
    let mut behavior = None;
    for mode in ["off", "capture", "reuse"] {
        let mut command = compiler(label, mode, false);
        let result = if error.is_some() { command.run_fail() } else { command.run() };
        let stderr = result.stderr_utf8();
        // No audit messages are removed or rewritten for this comparison.
        assert!(!stderr.contains("[hir-input-walk-audit]"), "{stderr}");
        if let Some(fragment) = error { assert!(stderr.contains(fragment), "{stderr}"); }
        if let Some(expected) = &diagnostics { assert_eq!(&stderr, expected); }
        else { diagnostics = Some(stderr); }
        if error.is_none() {
            let output = run("input_walk_audit").stdout_utf8();
            if let Some(expected) = &behavior { assert_eq!(&output, expected); }
            else { behavior = Some(output); }
        }
    }
}

fn accepted<'a>(output: &'a str, owner: &str) -> &'a str {
    let prefix = format!("[hir-input-walk-audit] accepted owner={owner} ");
    let rows: Vec<_> = output.lines().filter(|line| line.starts_with(&prefix)).collect();
    assert_eq!(rows.len(), 1, "expected exactly one completed audit for {owner}\n{output}");
    rows[0]
}

fn field(row: &str, name: &str) -> usize {
    let prefix = format!("{name}=");
    row.split_whitespace().find_map(|value| value.strip_prefix(&prefix))
        .unwrap().parse().unwrap()
}

fn reject(output: &str, owner: &str, reason: &str) {
    let expected = format!("[hir-input-walk-audit] rejected owner={owner} reason={reason}");
    assert_eq!(output.lines().filter(|line| *line == expected).count(), 1,
        "expected exact rejection {expected}\n{output}");
    assert!(!output.contains(&format!("[hir-input-walk-audit] accepted owner={owner} ")));
}

fn main() {
    inherited::run_all();
    let positive = rfs::read_to_string("literals-resolutions.rs");
    raw_control("literals", &positive, None);
    for mode in ["capture", "reuse"] {
        rfs::write("input.rs", &positive);
        let info = compiler("literals", mode, true).run().stderr_utf8();
        for owner in ["escaped_literals", "raw_literals", "underscored_numbers", "local_patterns",
                      "definitions", "local_call", "local_constructor", "external_constant", "trait_selection"] {
            assert!(field(accepted(&info, owner), "nodes") > 0);
        }
        let bindings = accepted(&info, "local_patterns");
        assert!(field(bindings, "params") > 0 && field(bindings, "body") > 0);
        let traits = accepted(&info, "trait_selection");
        assert!(field(traits, "traits") > 0 && field(traits, "candidates") > 0);
        assert!(field(accepted(&info, "external_constant"), "externals") > 0);
        run("input_walk_audit");
    }
    let rejected = rfs::read_to_string("rejected-gates.rs");
    raw_control("rejected", &rejected, None);
    for mode in ["capture", "reuse"] {
        rfs::write("input.rs", &rejected);
        let info = compiler("rejected", mode, true).run().stderr_utf8();
        for (owner, reason) in [
            ("rejected_typed_local", "body-local-type-or-super"),
            ("rejected_nested_item", "nested-item-or-unexpanded-statement"),
            ("rejected_closure", "unsupported-expression"),
            ("rejected_match", "unsupported-expression"),
            ("rejected_tuple_pattern", "unsupported-pattern"),
            ("rejected_coroutine", "coroutine-body"),
            ("rejected_type_arguments", "explicit-path-arguments"),
            ("rejected_external_call", "external-call-needs-current-legacy-proof"),
            ("rejected_hygiene", "nonroot-hygiene"),
        ] { reject(&info, owner, reason); }
        run("input_walk_audit");
    }
    for (label, owner, reason) in [
        ("literal-budget", "rejected_literal_budget", "literal-budget"),
        ("source-budget", "rejected_source_budget", "source-extent-budget"),
        ("node-budget", "rejected_node_budget", "node-budget"),
        ("depth-budget", "rejected_depth_budget", "expression-depth-budget"),
        ("identifier-budget", "rejected_identifier_budget", "identifier-budget"),
    ] {
        let source = rfs::read_to_string(format!("{label}.rs"));
        raw_control(label, &source, None);
        for mode in ["capture", "reuse"] {
            rfs::write("input.rs", &source);
            let info = compiler(label, mode, true).run().stderr_utf8();
            reject(&info, owner, reason);
            run("input_walk_audit");
        }
    }
    for (label, error) in [("invalid-suffix", "invalid suffix"),
                           ("invalid-escape", "unknown character escape"),
                           ("invalid-integer", "integer literal is too large")] {
        raw_control(label, &rfs::read_to_string(format!("{label}.rs")), Some(error));
    }
    rfs::write("input.rs", rfs::read_to_string("fixture.rs"));
}
