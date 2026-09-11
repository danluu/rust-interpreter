#[allow(dead_code)]
#[path = "../src/wrapper_route.rs"]
mod wrapper_route;

use wrapper_route::{Environment, Route, route};

fn selected() -> Environment {
    Environment {
        export_package: Some("example".into()),
        package: Some("example".into()),
        export_manifest: Some("/workspace/example".into()),
        manifest: Some("/workspace/example".into()),
        primary_package: true,
        ..Environment::default()
    }
}

fn invoke(extra: &[&str], env: &Environment) -> Result<Route, String> {
    let args = ["wrapper", "/toolchain/bin/rustc", "--crate-name", "example"]
        .into_iter()
        .chain(extra.iter().copied())
        .map(str::to_owned)
        .collect();
    route(args, env)
}

#[test]
fn package_and_manifest_both_identify_the_selected_library() {
    let mut env = selected();
    assert!(invoke(&["--crate-type", "lib"], &env).unwrap().export);
    for changed in ["package", "manifest", "primary", "missing-manifest"] {
        env = selected();
        match changed {
            "package" => env.package = Some("dependency".into()),
            "manifest" => env.manifest = Some("/other/example".into()),
            "primary" => env.primary_package = false,
            _ => env.manifest = None,
        }
        assert!(
            !invoke(&["--crate-type", "lib"], &env).unwrap().export,
            "{changed}"
        );
    }
}

#[test]
fn crate_name_selection_and_package_selection_can_be_combined() {
    let mut env = Environment {
        export_crate: Some("example".into()),
        ..Environment::default()
    };
    assert!(invoke(&["--crate-type", "rlib"], &env).unwrap().export);
    env.export_crate = Some("different".into());
    assert!(!invoke(&["--crate-type", "rlib"], &env).unwrap().export);
    env = selected();
    env.export_crate = Some("different".into());
    assert!(!invoke(&["--crate-type", "rlib"], &env).unwrap().export);
}

#[test]
fn no_selection_delegates_queries_and_libraries() {
    let env = Environment::default();
    for extra in [&["-vV"][..], &["--print", "cfg"], &["--crate-type", "rlib"]] {
        let route = invoke(extra, &env).unwrap();
        assert!(route.wrapper);
        assert!(!route.export);
        assert_eq!(route.args[0], "/toolchain/bin/rustc");
    }
}

#[test]
fn host_executables_and_proc_macros_do_not_select_package_library_export() {
    for kind in ["bin", "proc-macro", "cdylib"] {
        let route = invoke(&["--crate-type", kind], &selected()).unwrap();
        assert!(!route.export);
        assert!(!route.args.iter().any(|a| a == "-Zalways-encode-mir=yes"));
    }
}

#[test]
fn test_targets_require_test_mode_including_harness_false_cfg() {
    let env = Environment {
        export_test: true,
        ..selected()
    };
    assert!(!invoke(&["--crate-type", "lib"], &env).unwrap().export);
    for flags in [&["--test"][..], &["--cfg=test"], &["--cfg", "test"]] {
        let route = invoke(flags, &env).unwrap();
        assert!(route.export);
        assert_eq!(
            route.args.iter().filter(|s| *s == "--test").count(),
            usize::from(flags == ["--test"])
        );
    }
    assert!(!invoke(&["--cfg", "testing"], &env).unwrap().export);
}

#[test]
fn dependency_mir_flag_is_appended_after_existing_flags() {
    for kind in ["lib", "rlib", "rlib,cdylib"] {
        let route = invoke(
            &[
                "--crate-type",
                kind,
                "-Zalways-encode-mir=no",
                "--emit=metadata",
            ],
            &Environment::default(),
        )
        .unwrap();
        assert_eq!(route.args.last().unwrap(), "-Zalways-encode-mir=yes");
        assert!(route.args.iter().any(|s| s == "-Zalways-encode-mir=no"));
        assert!(route.args.iter().any(|s| s == "--emit=metadata"));
    }
}

fn std_env() -> Environment {
    Environment {
        std_sysroot: Some("/MIR sysroot".into()),
        std_target: Some("aarch64-apple-darwin".into()),
        ..selected()
    }
}

#[test]
fn target_sysroot_is_added_for_selected_and_unselected_units() {
    let mut env = std_env();
    for selected in [true, false] {
        env.primary_package = selected;
        for flags in [
            &["--target", "aarch64-apple-darwin"][..],
            &["--target=aarch64-apple-darwin"],
        ] {
            let route = invoke(flags, &env).unwrap();
            assert!(
                route
                    .args
                    .ends_with(&["--sysroot".into(), "/MIR sysroot".into()])
            );
        }
    }
}

#[test]
fn matching_explicit_sysroot_is_preserved_once() {
    for flags in [
        &["--target=aarch64-apple-darwin", "--sysroot", "/MIR sysroot"][..],
        &["--target", "aarch64-apple-darwin", "--sysroot=/MIR sysroot"],
    ] {
        let route = invoke(flags, &std_env()).unwrap();
        assert_eq!(route.args.len(), flags.len() + 3);
    }
}

#[test]
fn mismatched_target_or_sysroot_is_rejected_even_for_unselected_units() {
    let env = Environment {
        primary_package: false,
        ..std_env()
    };
    assert!(
        invoke(&["--target=x86_64-unknown-linux-gnu"], &env)
            .err()
            .unwrap()
            .contains("target does not match")
    );
    assert!(
        invoke(&["--target=aarch64-apple-darwin", "--sysroot=/other"], &env)
            .err()
            .unwrap()
            .contains("conflicts")
    );
    let env = Environment {
        std_target: None,
        ..env
    };
    assert!(invoke(&["--target=aarch64-apple-darwin"], &env).is_err());
}

#[test]
fn host_units_keep_their_sysroot_and_ordered_arguments() {
    let flags = [
        "--sysroot",
        "/host",
        "--crate-type",
        "proc-macro",
        "-C",
        "target-cpu=apple-m1",
        "path with spaces.rs",
    ];
    let route = invoke(&flags, &std_env()).unwrap();
    assert_eq!(&route.args[3..], flags);
    assert!(!route.export);
}

#[test]
fn standalone_export_does_not_apply_cargo_transformations() {
    let args = vec![
        "exporter".into(),
        "--crate-type".into(),
        "lib".into(),
        "--target=other".into(),
    ];
    let route = route(args.clone(), &std_env()).unwrap();
    assert!(!route.wrapper);
    assert!(route.export);
    assert_eq!(route.args, args);
}
