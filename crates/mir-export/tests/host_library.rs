#[allow(dead_code)]
#[path = "../src/wrapper_route.rs"]
mod wrapper_route;

use wrapper_route::{Environment, Route, route};

fn environment() -> Environment {
    Environment {
        std_sysroot: Some("/guest-sysroot".into()),
        std_target: Some("aarch64-apple-darwin".into()),
        export_package: Some("guest".into()),
        package: Some("dependency".into()),
        host_library_opt: Some("on".into()),
        ..Environment::default()
    }
}

fn invoke(flags: &[&str], env: &Environment) -> Result<Route, String> {
    route(["wrapper", "/toolchain/bin/rustc", "--crate-name", "example"]
        .into_iter().chain(flags.iter().copied()).map(str::to_owned).collect(), env)
}

fn library(extra: &[&str], env: &Environment) -> Result<Route, String> {
    let flags: Vec<_> = ["--crate-type", "rlib", "--emit=dep-info,metadata,link", "dep.rs"]
        .into_iter().chain(extra.iter().copied()).collect();
    invoke(&flags, env)
}

#[test]
fn opt_in_changes_only_host_library_codegen_and_keeps_light_wrapper() {
    for flags in [
        &["--crate-type", "rlib", "--emit=dep-info,metadata,link", "dep.rs"][..],
        &["--crate-type=lib", "--emit", "link=libdep.rlib", "dep.rs"],
    ] {
        let mut env = environment();
        env.host_library_opt = None;
        let original = invoke(flags, &env).unwrap().args;
        env.host_library_opt = Some("on".into());
        let optimized = invoke(flags, &env).unwrap();
        assert!(!optimized.export);
        assert!(!optimized.requires_exporter());
        assert!(optimized.host_library_opt);
        assert_eq!(&optimized.args[..original.len()], original);
        assert_eq!(&optimized.args[original.len()..], ["-Copt-level=1", "-Zmir-opt-level=1",
            "-Clto=off", "-Cdebug-assertions=yes", "-Coverflow-checks=yes"]);
        env.host_library_opt = Some("off".into());
        assert_eq!(invoke(flags, &env).unwrap().args, original);
    }
}

#[test]
fn effective_check_defaults_and_explicit_values_use_the_shared_parser() {
    for (flags, tail) in [
        (vec!["-Cdebug-assertions=no"], "-Coverflow-checks=no"),
        (vec!["-Cdebug_assertions=off", "--codegen", "debug-assertions=y"], "-Coverflow-checks=yes"),
        (vec!["-Cdebug-assertions=false", "-Coverflow_checks=yes"], "-Clto=off"),
        (vec!["-Coverflow-checks=no"], "-Cdebug-assertions=yes"),
    ] {
        let result = library(&flags, &environment()).unwrap();
        assert_eq!(result.args.last().unwrap(), tail);
        for flag in flags { assert!(result.args.contains(&flag.to_owned())); }
    }
    for flags in [
        &["-Cdebuginfo=2", "-Ccodegen-units=16", "-Cpanic=abort", "-Cincremental=cache"][..],
        &["--cfg", "feature=\"enabled\"", "-Ctarget-cpu=apple-m1", "-Clink-arg=-dead_strip"],
    ] {
        let result = library(flags, &environment()).unwrap();
        assert!(result.args.windows(flags.len()).any(|actual| actual == flags));
    }
}

#[test]
fn cargo_metadata_embedding_is_preserved_without_accepting_other_unstable_options() {
    for option in ["embed-metadata", "embed-metadata=no", "embed_metadata=false",
                   "embed-metadata=yes", "embed-metadata=on", "embed-metadata=n"] {
        for flags in [vec!["-Z".to_owned(), option.to_owned()], vec![format!("-Z{option}")]] {
            let borrowed: Vec<_> = flags.iter().map(String::as_str).collect();
            let mut env = environment();
            env.host_library_opt = None;
            let original = library(&borrowed, &env).unwrap();
            env.host_library_opt = Some("on".into());
            let optimized = library(&borrowed, &env).unwrap();
            assert_eq!(&optimized.args[..original.args.len()], original.args);
            assert!(optimized.args.iter().any(|arg| arg == "-Copt-level=1"));
        }
    }
    for option in ["embed-metadata=", "embed-metadata=0", "embed-metadata=unknown",
                   "embed-source=no", "mir-opt-level=1", "ub-checks=no"] {
        assert!(library(&["-Z", option], &environment()).is_err(), "{option}");
    }
    let mut macro_env = environment();
    macro_env.host_library_opt = None;
    macro_env.host_proc_macro_opt = Some("on".into());
    assert!(invoke(&["--crate-type=proc-macro", "--emit=link", "macro.rs",
                     "-Z", "embed-metadata=no"], &macro_env).is_err());
}

#[test]
fn guest_macro_build_executable_probe_metadata_and_selected_export_keep_arguments() {
    for flags in [
        &["--crate-type", "rlib", "--emit=dep-info,metadata,link", "--target=aarch64-apple-darwin", "dep.rs"][..],
        &["--crate-type", "proc-macro", "--emit=link", "macro.rs"],
        &["--crate-type", "bin", "--emit=link", "build.rs"],
        &["--crate-type=cdylib", "--emit=link", "lib.rs"],
        &["--crate-type=rlib", "--emit=metadata", "dep.rs"],
        &["--crate-type=rlib", "--emit=link", "--test", "dep.rs"],
        &["--crate-type=rlib", "--print=cfg", "-Copt-level=3", "-"],
        &["-vV"],
    ] {
        let mut env = environment();
        env.host_library_opt = None;
        let original = invoke(flags, &env).unwrap().args;
        env.host_library_opt = Some("on".into());
        assert_eq!(invoke(flags, &env).unwrap().args, original, "{flags:?}");
    }
    let mut env = environment();
    env.export_package = None;
    env.export_crate = Some("example".into());
    let result = library(&[], &env).unwrap();
    assert!(result.export);
    assert!(!result.args.iter().any(|arg| arg == "-Copt-level=1"));
}

#[test]
fn conflicting_optimization_and_ambiguous_roles_fail_without_overrides() {
    for flags in [
        &["-O"][..], &["-Copt-level=0"], &["-C", "opt_level=3"],
        &["--codegen=opt-level=1"], &["-Clto=off"], &["-Zmir-opt-level=1"],
        &["-Zub-checks=no"], &["-Zthreads=2"], &["--jobs-frontend=2"],
        &["-Cllvm-args=-inline-threshold=1"], &["-Cprofile-generate=profiles"],
        &["-Cdebug-assertions=0"], &["-Coverflow-checks=1"], &["@flags"],
        &["--sysroot=/other"], &["--emit=link"], &["--crate-type=lib"],
        &["second.rs"], &["--unknown"], &["-C"],
    ] { assert!(library(flags, &environment()).is_err(), "{flags:?}"); }
    for flags in [
        &["--crate-type=rlib,proc-macro", "--emit=link", "dep.rs"][..],
        &["--crate-type=lib,rlib", "--emit=link", "dep.rs"],
        &["--crate-type=rlib", "--emit=link,llvm-ir", "dep.rs"],
        &["--crate-type=rlib", "--emit=link", "-"],
        &["--crate-type=rlib", "--emit=link", "--", "dep.rs"],
        &["@hidden-guest-flags"],
    ] { assert!(invoke(flags, &environment()).is_err(), "{flags:?}"); }
    let result = library(&["--cfg", "-Copt-level=3"], &environment()).unwrap();
    assert!(result.args.iter().any(|arg| arg == "-Copt-level=1"));
    let result = invoke(&["--crate-type=bin", "--emit=link", "build.rs", "--cfg", "--crate-type=rlib"], &environment()).unwrap();
    assert!(!result.args.iter().any(|arg| arg == "-Copt-level=1"));
}

#[test]
fn missing_context_and_mixed_policies_are_rejected() {
    for value in ["", "1", "true"] {
        let mut env = environment(); env.host_library_opt = Some(value.into());
        assert!(library(&[], &env).is_err());
    }
    for field in [0, 1, 2, 3, 4, 5, 6] {
        let mut env = environment();
        match field {
            0 => env.std_sysroot = None,
            1 => env.std_target = Some(String::new()),
            2 => env.borrowck_cache = Some("verify".into()),
            3 => env.compiler_rustc = Some("/toolchain/bin/rustc".into()),
            4 => env.frontend_workers = Some("1".into()),
            5 => env.host_proc_macro_opt = Some("on".into()),
            _ => env.stable_mono_cgu_partitioning = Some("off".into()),
        }
        assert!(library(&[], &env).is_err());
    }
    assert!(library(&[], &environment()).unwrap().check_compiler(std::path::Path::new("/missing")).is_err());
    assert!(route(vec!["exporter".into(), "file.rs".into()], &environment()).is_err());
}
