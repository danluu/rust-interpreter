//@ ignore-cross-compile

use std::path::{Path, PathBuf};

use run_make_support::{Rustc, rfs, run, rustc};

fn compiler(enabled: bool, info: bool) -> Rustc {
    let mut command = rustc();
    command.input("library.rs").crate_name("hir_owner_test").crate_type("rlib")
        .output("libhir_owner_test.rlib").metadata("hir_owner_reuse_test")
        .incremental(if enabled { "cache-on" } else { "cache-off" })
        .arg(format!("-Zreuse-hir-owners={enabled}"))
        .arg("-Cdebuginfo=2").arg("--edition=2024");
    if info { command.arg("-Zincremental-info"); }
    command
}

fn source(delta: usize, prefix: &str) -> String {
    format!(
        "#![allow(dead_code, non_camel_case_types)]\n{prefix}\n\
         pub fn anchor(x: u64) -> u64 {{ let twice = x * 2; (twice + 3) }}\n\
         pub fn changed(x: u64) -> u64 {{ x + {delta} }}\n\
         pub fn scalar_float(x: f64) -> f64 {{ (x * 1.5) + 2.0 }}\n\
         pub fn scalar_char(x: char) -> bool {{ x == 'λ' }}\n\
         pub fn shadow(x: u64) -> u64 {{ let y = {{ let x = x + 1; x }}; y + x }}\n\
         pub fn empty() {{}}\n\
         #[inline(never)] pub fn attributed(x: u64) -> u64 {{ x + 7 }}\n\
         pub fn generic<T: Copy>(x: T) -> T {{ x }}\n\
         pub fn lifetime(x: &u64) -> &u64 {{ x }}\n\
         pub fn closure(x: u64) -> u64 {{ (|| x + 9)() }}\n\
         pub fn expansion() -> u32 {{ line!() }}\n"
    )
}

fn execute(delta: usize) -> String {
    rfs::write("main.rs", format!(
        "extern crate hir_owner_test as t; fn main() {{\n\
         assert_eq!(t::anchor(5), 13); assert_eq!(t::changed(5), 5 + {delta});\n\
         assert_eq!(t::scalar_float(2.0), 5.0); assert!(t::scalar_char('λ'));\n\
         assert_eq!(t::shadow(5), 11); t::empty();\n\
         assert_eq!(t::attributed(1), 8); assert_eq!(t::generic(4_u8), 4);\n\
         assert_eq!(*t::lifetime(&3), 3); assert_eq!(t::closure(1), 10);\n\
         println!(\"{{}} {{}} {{}}\", t::anchor(5), t::changed(5), t::expansion()); }}"
    ));
    rustc().input("main.rs").extern_("hir_owner_test", "libhir_owner_test.rlib").run();
    run("main").stdout_utf8()
}

fn successful(delta: usize, prefix: &str, expect_anchor_hit: bool) {
    rfs::write("library.rs", source(delta, prefix));
    compiler(false, false).run();
    let ordinary = execute(delta);
    let stderr = compiler(true, true).run().stderr_utf8();
    let candidate = execute(delta);
    assert_eq!(ordinary, candidate);
    if expect_anchor_hit { assert!(stderr.contains("[hir-owner-reuse] hit function anchor"), "{stderr}"); }
    else { assert!(stderr.contains("[hir-owner-reuse] miss function anchor"), "{stderr}"); }
    for name in ["attributed", "generic", "lifetime", "closure", "expansion"] {
        assert!(stderr.contains(&format!("[hir-owner-reuse] rejected-input function {name}")), "{stderr}");
    }
}

fn records(directory: &Path, output: &mut Vec<PathBuf>) {
    for entry in std::fs::read_dir(directory).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() { records(&path, output); }
        else if path.file_name().unwrap().to_string_lossy().starts_with("hir-owner-reuse-v1-")
            && path.extension().is_some_and(|ext| ext == "bin") { output.push(path); }
    }
}

fn main() {
    successful(1, "", false);
    successful(17, "// A genuine unequal-width edit before all owners: λ\n", true);
    successful(1, "", true);

    // Same function syntax now resolves u64 to an application type. It must take stock lowering.
    rfs::write("library.rs", source(1, "type u64 = u32;"));
    compiler(false, false).run();
    let ordinary = execute(1);
    let stderr = compiler(true, true).run().stderr_utf8();
    assert!(stderr.contains("[hir-owner-reuse] rejected-input function anchor"), "{stderr}");
    assert_eq!(ordinary, execute(1));
    successful(1, "", true);

    for (extra, code) in [
        ("fn uncalled() -> u64 { true }", "E0308"),
        ("fn uncalled() { let value = String::from(\"a\"); let moved = value; drop(value); }", "E0382"),
        ("const UNUSED: u64 = 1 / 0;", "E0080"),
        ("fn uncalled() -> u64 { 1 / 0 }", "unconditional_panic"),
    ] {
        rfs::write("library.rs", format!("{}\n{extra}\n", source(1, "")));
        let ordinary = compiler(false, false).arg("--error-format=json").run_fail().stderr_utf8();
        let candidate = compiler(true, false).arg("--error-format=json").run_fail().stderr_utf8();
        assert!(ordinary.contains(code), "{ordinary}");
        assert_eq!(ordinary, candidate);
        successful(1, "", true);
    }

    let mut paths = Vec::new();
    records(Path::new("cache-on"), &mut paths);
    assert!(!paths.is_empty());
    for path in &paths { rfs::write(path, b"{\"truncated\":"); }
    successful(23, "// Fresh edit with damaged sidecars\n", false);
    successful(1, "", true);

    // A changed tracked option must invalidate the normal incremental session and its sidecars.
    let stderr = compiler(true, true).arg("-Cdebug-assertions=no").run().stderr_utf8();
    assert!(stderr.contains("[hir-owner-reuse] miss function anchor"), "{stderr}");
    execute(1);
}
