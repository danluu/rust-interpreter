#[allow(dead_code)]
#[path = "/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/host-wrapper-opt-01/crates/mir-export/src/wrapper_route.rs"]
mod wrapper_route;
use wrapper_route::{Environment, route};

fn env() -> Environment {
    Environment { compiler_rustc: Some("/runtime/bin/rustc".into()),
        frontend_compiler: Some("/runtime/bin/rustc".into()),
        stable_cgu_partitioning: Some("off".into()),
        std_sysroot: Some("/guest".into()), std_target: Some("aarch64-apple-darwin".into()),
        export_package: Some("selected".into()), package: Some("dependency".into()),
        host_codegen_opt: Some("on".into()), ..Environment::default() }
}
fn call(args: &[&str], env: &Environment) -> Result<wrapper_route::Route, String> {
    route(["wrapper", "/runtime/bin/rustc"].into_iter().chain(args.iter().copied()).map(str::to_owned).collect(), env)
}
fn unit(kind: &str, extra: &[&str], env: &Environment) -> Result<wrapper_route::Route, String> {
    let mut args = vec!["--crate-name", "unit", "--crate-type", kind, "--emit=dep-info,link", "lib.rs"];
    args.extend(extra); call(&args, env)
}

#[test]
fn both_host_roles_add_one_suffix_after_unchanged_runtime_routing() {
    for kind in ["proc-macro", "lib", "rlib"] {
        let mut e = env(); e.host_codegen_opt = None;
        let off = unit(kind, &["-Cmetadata=abc", "-Cextra-filename=-xyz"], &e).unwrap();
        e.host_codegen_opt = Some("on".into());
        let on = unit(kind, &["-Cmetadata=abc", "-Cextra-filename=-xyz"], &e).unwrap();
        assert_eq!(&on.args[..off.args.len()], off.args);
        assert_eq!(&on.args[off.args.len()..], ["-Copt-level=3", "-Zmir-opt-level=1", "-Clto=off", "-Cdebug-assertions=yes", "-Coverflow-checks=yes"]);
        assert!(!on.requires_exporter());
        assert!(on.args.contains(&"-Zstable-cgu-partitioning=no".to_owned()));
        assert_eq!(on.args.iter().filter(|x| *x == "-Copt-level=3").count(), 1);
    }
}

#[test]
fn nonhost_nonlinked_selected_and_probe_arguments_do_not_change() {
    let cases: &[(&str, &[&str])] = &[("bin", &[]), ("cdylib", &[]),
        ("lib", &["--target=aarch64-apple-darwin"]), ("proc-macro", &["--test"])];
    for &(kind, extra) in cases {
        let mut e=env(); e.host_codegen_opt=None; let off=unit(kind,extra,&e).unwrap();
        e.host_codegen_opt=Some("on".into()); assert_eq!(unit(kind,extra,&e).unwrap().args,off.args);
    }
    for args in [vec!["-vV"], vec!["--crate-type=lib", "--emit=metadata", "lib.rs"]] {
        let mut e=env();e.host_codegen_opt=None;let off=call(&args,&e).unwrap();
        e.host_codegen_opt=Some("on".into());assert_eq!(call(&args,&e).unwrap().args,off.args);
    }
    let mut e=env();e.export_package=None;e.export_crate=Some("unit".into());
    let selected=unit("lib",&[],&e).unwrap();assert!(selected.export);
    assert!(!selected.args.contains(&"-Copt-level=3".to_owned()));
}

#[test]
fn explicit_checks_and_metadata_embedding_keep_original_semantics() {
    for kind in ["proc-macro", "rlib"] {
        let on=unit(kind,&["-Cdebug-assertions=no"],&env()).unwrap();
        assert!(!on.args.contains(&"-Cdebug-assertions=yes".to_owned()));
        assert_eq!(on.args.last().unwrap(),"-Coverflow-checks=no");
        let on=unit(kind,&["-Cdebug-assertions=no","-Coverflow-checks=yes"],&env()).unwrap();
        assert_eq!(on.args.last().unwrap(),"-Clto=off");
    }
    assert!(unit("rlib",&["-Zembed-metadata=no"],&env()).is_ok());
    assert!(unit("proc-macro",&["-Zembed-metadata=no"],&env()).is_err());
}

#[test]
fn ambiguous_and_user_optimization_inputs_still_refuse() {
    for kind in ["proc-macro", "rlib"] {
        for extra in [vec!["-O"],vec!["-Copt-level=0"],vec!["-Clto=off"],vec!["-Zmir-opt-level=1"],
            vec!["-Zub-checks=no"],vec!["@hidden"],vec!["-Cunknown"],vec!["second.rs"],vec!["--crate-type=bin"]] {
            assert!(unit(kind,&extra,&env()).is_err(),"{kind}: {extra:?}");
        }
    }
}

#[test]
fn runtime_and_conflicting_policy_guards_remain_closed() {
    for fault in 0..9 {
        let mut e=env();match fault {
            0=>e.compiler_rustc=None, 1=>e.frontend_compiler=Some("/build/bin/rustc".into()),
            2=>e.std_target=None, 3=>e.stable_cgu_partitioning=Some("on".into()),
            4=>e.host_proc_macro_opt=Some("on".into()),5=>e.host_library_opt=Some("on".into()),
            6=>e.borrowck_cache=Some("reuse".into()),7=>e.frontend_workers=Some("1".into()),
            _=>e.host_codegen_opt=Some("3".into()),
        };assert!(unit("lib",&[],&e).is_err(),"fault {fault}");
    }
    assert!(unit("lib",&[],&env()).unwrap().check_compiler(std::path::Path::new("/missing")).is_err());
}

#[test]
fn legacy_o1_vector_stays_distinct_from_new_o3() {
    let mut e=env();e.compiler_rustc=None;e.stable_cgu_partitioning=None;e.host_codegen_opt=None;e.host_library_opt=Some("on".into());
    let old=unit("lib",&[],&e).unwrap();assert!(old.args.contains(&"-Copt-level=1".to_owned()));
    assert!(!old.args.contains(&"-Copt-level=3".to_owned()));
    e.host_proc_macro_opt=Some("on".into());assert!(unit("lib",&[],&e).is_err());
}
