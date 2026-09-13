#[allow(dead_code)]
#[path = "../src/wrapper_route.rs"]
mod wrapper_route;

use wrapper_route::{BorrowckCacheMode, Environment, Route, route};

fn frontend_env(workers: &str) -> Environment {
    Environment {
        frontend_workers: Some(workers.into()),
        frontend_compiler: Some("/toolchain/bin/rustc".into()),
        ..selected()
    }
}

#[test]
fn frontend_workers_reach_every_cargo_role_without_changing_backend_flags() {
    for workers in ["1", "2"] {
        for kind in ["rlib", "bin", "proc-macro", "cdylib"] {
            for guest in [false, true] {
                let mut flags = vec!["--crate-type", kind, "--jobs-backend=2", "--jobs-linker=1",
                    "-Copt-level=1", "-Ccodegen-units=16", "source.rs"];
                if guest { flags.push("--target=aarch64-apple-darwin"); }
                let result = invoke(&flags, &frontend_env(workers)).unwrap();
                assert_eq!(&result.args[3..3 + flags.len()], flags);
                assert_eq!(result.args.iter().filter(|arg| arg.starts_with("-Zthreads=")).count(), 1);
                assert!(result.args.contains(&format!("-Zthreads={workers}")));
                assert_eq!(result.export, kind == "rlib");
            }
        }
    }
}

#[test]
fn frontend_policy_rejects_conflicting_flags_response_files_and_unpinned_routes() {
    for flags in [
        &["-Zthreads=1"][..], &["-Z", "threads=2"], &["--jobs-frontend=2"],
        &["--jobs-frontend", "1"], &["--jobs=2"], &["-j2"], &["-j", "2"],
        &["@arguments"], &["-Zstable-cgu-partitioning=no"],
        &["-Zstable-mono-cgu-partitioning=yes"], &["-Z", "proc_macro_execution_strategy=cross-thread"],
    ] {
        assert!(invoke(flags, &frontend_env("2")).is_err(), "{flags:?}");
    }
    for workers in ["", "0", "3", "sync", "01"] {
        assert!(invoke(&["-vV"], &frontend_env(workers)).is_err());
    }
    let mut env = frontend_env("2");
    env.frontend_compiler = Some("/other/rustc".into());
    assert!(invoke(&["source.rs"], &env).is_err());
    assert!(route(vec!["exporter".into(), "source.rs".into()], &frontend_env("2")).is_err());
}

#[test]
fn frontend_policy_preserves_selection_and_requires_no_exporter_for_native_work() {
    let mut env = frontend_env("2");
    env.primary_package = false;
    for flags in [&["-vV"][..], &["--crate-type", "bin", "source.rs"],
        &["--crate-type", "rlib", "source.rs"]] {
        let result = invoke(flags, &env).unwrap();
        assert!(!result.export);
        assert!(!result.requires_exporter());
    }
    env.conflicting_frontend_policy = true;
    assert!(invoke(&["-vV"], &env).is_err());
    env.conflicting_frontend_policy = false;
    env.borrowck_cache = Some("verify".into());
    assert!(invoke(&["source.rs"], &env).is_err());
}

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
fn custom_policy_reaches_host_and_guest_without_changing_existing_arguments() {
    for policy in ["off", "on"] {
        for primary in [false, true] {
            for flags in [
                &["--crate-type", "rlib", "--emit=dep-info,metadata,link"][..],
                &["--crate-type", "proc-macro", "--emit=link"],
                &["--crate-type", "bin", "--emit=link"],
                &["--crate-type", "rlib", "--target=aarch64-apple-darwin", "--emit=metadata"],
            ] {
                let mut env = std_env();
                env.primary_package = primary;
                let original = invoke(flags, &env).unwrap();
                env.compiler_rustc = Some("/toolchain/bin/rustc".into());
                env.stable_cgu_partitioning = Some(policy.into());
                let custom = invoke(flags, &env).unwrap();
                assert!(custom.custom_compiler);
                assert_eq!(custom.export, original.export);
                let expected = format!("-Zstable-cgu-partitioning={}", if policy == "on" { "yes" } else { "no" });
                assert_eq!(custom.args.iter().filter(|arg| **arg == expected).count(), 1);
                assert_eq!(custom.args.into_iter().filter(|arg| *arg != expected).collect::<Vec<_>>(), original.args);
            }
        }
    }
}

#[test]
fn custom_policy_rejects_incomplete_settings_response_files_and_flag_conflicts() {
    let mut env = selected();
    env.compiler_rustc = Some("/toolchain/bin/rustc".into());
    assert!(invoke(&[], &env).is_err());
    for policy in ["", "yes", "invalid"] {
        env.stable_cgu_partitioning = Some(policy.into());
        assert!(invoke(&[], &env).is_err());
    }
    env.stable_cgu_partitioning = Some("on".into());
    for flags in [
        &["@response-file"][..], &["-Zstable-cgu-partitioning=yes"],
        &["-Z", "stable-cgu-partitioning=no"], &["-Zstable_cgu_partitioning=yes"],
        &["--sysroot=/another/compiler"],
    ] {
        assert!(invoke(flags, &env).is_err(), "{flags:?}");
    }
    env.compiler_rustc = Some("/another/bin/rustc".into());
    assert!(invoke(&[], &env).is_err());
    env.compiler_rustc = None;
    assert!(invoke(&[], &env).is_err());
}

#[test]
fn compiler_guard_covers_selected_exports_and_custom_native_jobs() {
    let root = std::env::temp_dir().join(format!("rust-interp-compiler-route-{}-{}", std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
    std::fs::create_dir_all(root.join("bin")).unwrap();
    std::fs::write(root.join("bin/rustc"), b"fixture").unwrap();
    let rustc = root.join("bin/rustc").to_string_lossy().into_owned();
    for primary in [false, true] {
        let mut env = selected();
        env.primary_package = primary;
        env.compiler_rustc = Some(rustc.clone().into());
        env.stable_cgu_partitioning = Some("off".into());
        let invocation = route(["wrapper", &rustc, "--crate-type", "rlib"].map(str::to_owned).to_vec(), &env).unwrap();
        assert!(invocation.check_compiler(&root).is_ok());
        assert!(invocation.check_compiler(&root.join("different")).is_err());
    }
    let invocation = route(["wrapper", &rustc, "--crate-type", "rlib"].map(str::to_owned).to_vec(), &selected()).unwrap();
    assert!(invocation.check_compiler(&root).is_ok());
    assert!(invocation.check_compiler(&root.join("different")).is_err());
    std::fs::remove_dir_all(root).unwrap();
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

#[test]
fn borrowck_cache_modes_require_explicit_valid_values() {
    assert_eq!(BorrowckCacheMode::parse(None).unwrap(), BorrowckCacheMode::Off);
    for (value, expected) in [
        ("off", BorrowckCacheMode::Off),
        ("verify", BorrowckCacheMode::Verify),
        ("reuse", BorrowckCacheMode::Reuse),
    ] {
        let env = Environment {
            borrowck_cache: Some(value.into()),
            ..Environment::default()
        };
        assert_eq!(invoke(&["source.rs"], &env).unwrap().borrowck_cache, expected);
    }
    for value in ["", "auto", "Verify", "reuse ", "/some/cache"] {
        let env = Environment {
            borrowck_cache: Some(value.into()),
            ..Environment::default()
        };
        // Invalid configuration fails even on a probe or an export selection.
        assert!(invoke(&["-vV"], &env).err().unwrap().contains("must be off, verify, or reuse"));
        assert!(invoke(&["source.rs"], &env).is_err());
    }
}

#[cfg(unix)]
#[test]
fn borrowck_cache_rejects_non_unicode_environment_values() {
    use std::os::unix::ffi::OsStringExt;
    let env = Environment {
        borrowck_cache: Some(std::ffi::OsString::from_vec(vec![255])),
        ..Environment::default()
    };
    assert!(invoke(&["source.rs"], &env).is_err());
}

#[test]
fn opt_in_routes_all_compilation_units_without_selecting_their_export() {
    for value in ["verify", "reuse"] {
        let env = Environment {
            borrowck_cache: Some(value.into()),
            ..Environment::default()
        };
        for kind in ["lib", "rlib", "bin", "proc-macro", "cdylib"] {
            let route = invoke(&["--crate-type", kind, "source.rs"], &env).unwrap();
            assert!(!route.export);
            assert!(route.requires_exporter(), "{value}: {kind}");
        }
        for input in ["-", "source", "path with spaces.rs", "@compiler-args"] {
            let route = invoke(&[input], &env).unwrap();
            assert!(!route.export);
            assert!(route.requires_exporter(), "{value}: {input}");
        }
    }
    for value in [None, Some("off")] {
        let env = Environment {
            borrowck_cache: value.map(Into::into),
            ..Environment::default()
        };
        assert!(!invoke(&["source.rs"], &env).unwrap().requires_exporter());
    }
    assert!(invoke(&["--crate-type", "lib", "source.rs"], &selected()).unwrap().requires_exporter());
}

#[test]
fn opt_in_keeps_known_rustc_metadata_probes_on_the_light_route() {
    let env = Environment {
        borrowck_cache: Some("reuse".into()),
        ..Environment::default()
    };
    for extra in [
        &["-vV"][..],
        &["--version"],
        &["--print", "cfg"],
        &["--print=sysroot"],
        &["-", "--crate-type", "bin", "--print=file-names", "--print=sysroot", "--print=split-debuginfo", "--print=crate-name", "--print=cfg"],
    ] {
        let route = invoke(extra, &env).unwrap();
        assert!(!route.export);
        assert!(!route.requires_exporter(), "{extra:?}");
    }
}

#[test]
fn compilation_outputs_and_ambiguous_queries_keep_requested_callbacks() {
    let env = Environment {
        borrowck_cache: Some("verify".into()),
        ..Environment::default()
    };
    for extra in [
        &["source.rs", "--emit=metadata", "--print=cfg"][..],
        &["source.rs", "--emit", "link", "--print", "cfg"],
        &["source.rs", "--print=link-args"],
        &["source.rs", "--print=native-static-libs"],
        &["--print=cfg", "--print=unknown"],
        &["--print=cfg", "@compiler-args"],
        &["source.rs", "--print=cfg"],
        &["--out-dir", "--print=cfg", "source.rs"],
        &["--sysroot", "--print=cfg", "source.rs"],
        &["--", "--print=cfg"],
        &["--print"],
    ] {
        let route = invoke(extra, &env).unwrap();
        assert!(!route.export);
        assert!(route.requires_exporter(), "{extra:?}");
    }
}
