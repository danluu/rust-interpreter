#[allow(dead_code)]
#[path = "../src/wrapper_route.rs"]
mod wrapper_route;

use wrapper_route::{Environment, route};

fn environment() -> Environment {
    Environment { std_sysroot: Some("/guest-sysroot".into()),
        std_target: Some("aarch64-apple-darwin".into()),
        export_package: Some("guest".into()), package: Some("macros".into()),
        host_proc_macro_opt: Some("on".into()), ..Environment::default() }
}

fn invoke(flags: &[&str], env: &Environment) -> Result<wrapper_route::Route, String> {
    route(["wrapper", "/toolchain/bin/rustc", "--crate-name", "example"]
        .into_iter().chain(flags.iter().copied()).map(str::to_owned).collect(), env)
}

fn macro_flags(extra: &[&str]) -> Vec<String> {
    ["--crate-type", "proc-macro", "--emit=dep-info,link", "macro.rs"]
        .into_iter().chain(extra.iter().copied()).map(str::to_owned).collect()
}

fn run_macro(extra: &[&str], env: &Environment) -> Result<wrapper_route::Route, String> {
    let flags = macro_flags(extra);
    invoke(&flags.iter().map(String::as_str).collect::<Vec<_>>(), env)
}

#[test]
fn off_on_off_preserves_arguments_and_only_changes_actual_host_macro() {
    let mut env = environment();
    for flags in [
        &["--crate-type", "proc-macro", "--emit=dep-info,link", "macro.rs"][..],
        &["--crate-type=proc-macro", "--emit", "link=macro.dylib", "macro.rs"],
    ] {
        env.host_proc_macro_opt = Some("off".into());
        let original = invoke(flags, &env).unwrap().args;
        env.host_proc_macro_opt = Some("on".into());
        let optimized = invoke(flags, &env).unwrap();
        assert!(!optimized.export);
        assert_eq!(&optimized.args[..original.len()], original);
        assert_eq!(&optimized.args[original.len()..], ["-Copt-level=1", "-Zmir-opt-level=1",
            "-Clto=off", "-Cdebug-assertions=yes", "-Coverflow-checks=yes"]);
        env.host_proc_macro_opt = None;
        assert_eq!(invoke(flags, &env).unwrap().args, original);
    }
}

#[test]
fn preserves_effective_checks_including_false_and_rightmost_explicit_values() {
    let env = environment();
    for (flags, overflow) in [
        (vec!["-Cdebug-assertions=no"], Some("-Coverflow-checks=no")),
        (vec!["-C", "debug_assertions=off", "-Cdebug-assertions=y"], Some("-Coverflow-checks=yes")),
        (vec!["--codegen", "debug-assertions=false", "-Coverflow-checks=yes"], None),
        (vec!["-Cdebug-assertions", "-C", "overflow_checks=n"], None),
    ] {
        let actual = run_macro(&flags, &env).unwrap().args;
        assert!(!actual.iter().any(|arg| arg == "-Cdebug-assertions=yes"));
        if let Some(flag) = overflow { assert_eq!(actual.last().unwrap(), flag); }
        else { assert_eq!(actual.last().unwrap(), "-Clto=off"); }
    }
    for invalid in ["-Cdebug-assertions=0", "-Coverflow-checks=1"] {
        assert!(run_macro(&[invalid], &env).is_err());
    }
}

#[test]
fn probes_guest_metadata_tests_and_other_host_roles_keep_baseline_arguments() {
    let mut env = environment();
    for flags in [
        &["--crate-type", "rlib", "--emit=dep-info,metadata,link", "dep.rs"][..],
        &["--crate-type", "bin", "--emit=link", "build.rs"],
        &["--crate-type", "cdylib", "--emit=link", "lib.rs"],
        &["--crate-type", "proc-macro", "--emit=metadata", "macro.rs"],
        &["--crate-type", "proc-macro", "--emit=link", "--target=aarch64-apple-darwin", "macro.rs"],
        &["--crate-type", "proc-macro", "--emit=link", "--test", "macro.rs"],
        &["--crate-type", "proc-macro", "--print=cfg", "-Copt-level=3", "-"],
        &["-vV"],
    ] {
        env.host_proc_macro_opt = None;
        let original = invoke(flags, &env).unwrap().args;
        env.host_proc_macro_opt = Some("on".into());
        assert_eq!(invoke(flags, &env).unwrap().args, original, "{flags:?}");
    }
    // Explicit crate selection can otherwise select a proc macro for export.
    env.export_package = None;
    env.export_crate = Some("example".into());
    let selected = run_macro(&[], &env).unwrap();
    assert!(selected.export);
    assert!(!selected.args.iter().any(|arg| arg == "-Copt-level=1"));
}

#[test]
fn hidden_ambiguous_or_user_optimization_settings_are_never_overridden() {
    let env = environment();
    for flags in [
        &["-O"][..], &["-Copt-level=0"], &["-C", "opt_level=3"],
        &["--codegen=opt-level=1"], &["-Clto=off"], &["-C", "lto=thin"],
        &["-Cllvm-args=-inline-threshold=1"], &["-Cprofile-generate=profiles"],
        &["-Cinstrument-coverage"], &["-Zmir-opt-level=1"], &["-Z", "mir_opt_level=0"],
        &["-Zub-checks=no"], &["@flags"], &["--sysroot=/other"],
        &["--emit=link"], &["--crate-type=rlib"], &["second.rs"],
        &["--unknown", "--crate-type=proc-macro"], &["-C"],
    ] {
        assert!(run_macro(flags, &env).is_err(), "{flags:?}");
    }
    for flags in [
        &["--crate-type=proc-macro,rlib", "--emit=link", "macro.rs"][..],
        &["--crate-type=proc-macro", "--emit=link,llvm-ir", "macro.rs"],
        &["--crate-type=proc-macro", "--emit=link", "-"],
        &["--crate-type=proc-macro", "--emit=link", "--", "macro.rs"],
    ] { assert!(invoke(flags, &env).is_err(), "{flags:?}"); }
}

#[test]
fn option_values_cannot_impersonate_role_or_target_flags() {
    let env = environment();
    let flags = ["--crate-type=rlib", "--emit=link", "dep.rs", "--cfg", "--crate-type=proc-macro"];
    let actual = invoke(&flags, &env).unwrap();
    assert!(!actual.args.iter().any(|arg| arg == "-Copt-level=1"));
    let actual = run_macro(&["--cfg", "-Copt-level=3"], &env).unwrap();
    assert!(actual.args.iter().any(|arg| arg == "-Copt-level=1"));
}

#[test]
fn missing_context_invalid_policy_and_compiler_mismatch_fail_closed() {
    for value in ["", "1", "true"] {
        let mut env = environment(); env.host_proc_macro_opt = Some(value.into());
        assert!(run_macro(&[], &env).is_err());
    }
    let mut env = environment(); env.std_target = None;
    assert!(run_macro(&[], &env).is_err());
    env = environment(); env.borrowck_cache = Some("reuse".into());
    assert!(run_macro(&[], &env).is_err());
    env = environment(); env.compiler_rustc = Some("/toolchain/bin/rustc".into());
    assert!(run_macro(&[], &env).is_err());
    assert!(run_macro(&[], &environment()).unwrap().check_compiler(std::path::Path::new("/missing")).is_err());
    assert!(route(vec!["exporter".into(), "file.rs".into()], &environment()).is_err());
}
