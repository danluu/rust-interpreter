//! Cargo invocation routing shared by the standalone exporter and light wrapper.
//! Keep this module independent of rustc_driver and of exporter dependencies.
use std::ffi::OsString;
use std::path::{Path, PathBuf};

#[derive(Default)]
pub struct Environment {
    pub std_sysroot: Option<String>,
    pub std_target: Option<String>,
    pub export_crate: Option<String>,
    pub export_package: Option<String>,
    pub export_manifest: Option<OsString>,
    pub export_test: bool,
    pub package: Option<String>,
    pub primary_package: bool,
    pub manifest: Option<OsString>,
}

impl Environment {
    pub fn read() -> Self {
        Self {
            std_sysroot: std::env::var("RUST_INTERP_STD_SYSROOT").ok(),
            std_target: std::env::var("RUST_INTERP_STD_TARGET").ok(),
            export_crate: std::env::var("RUST_INTERP_EXPORT_CRATE").ok(),
            export_package: std::env::var("RUST_INTERP_EXPORT_PACKAGE").ok(),
            export_manifest: std::env::var_os("RUST_INTERP_EXPORT_MANIFEST"),
            export_test: std::env::var("RUST_INTERP_EXPORT_TEST").is_ok_and(|s| s == "1"),
            package: std::env::var("CARGO_PKG_NAME").ok(),
            primary_package: std::env::var_os("CARGO_PRIMARY_PACKAGE").is_some(),
            manifest: std::env::var_os("CARGO_MANIFEST_DIR"),
        }
    }
}

pub struct Route {
    /// Real compiler argv in wrapper mode, original argv in standalone mode.
    pub args: Vec<String>,
    pub wrapper: bool,
    pub export: bool,
}

pub fn route(mut args: Vec<String>, env: &Environment) -> Result<Route, String> {
    // Preserve the existing wrapper convention, including standalone exports.
    let wrapper = args
        .get(1)
        .is_some_and(|s| Path::new(s).file_stem().is_some_and(|s| s == "rustc"));
    if wrapper {
        args.remove(0);
    }
    if wrapper && let Some(sysroot) = &env.std_sysroot {
        let value = |flag: &str| {
            args.iter().enumerate().find_map(|(index, arg)| {
                arg.strip_prefix(&format!("{flag}="))
                    .map(str::to_owned)
                    .or_else(|| {
                        (arg == flag)
                            .then(|| args.get(index + 1).cloned())
                            .flatten()
                    })
            })
        };
        // An explicit target identifies guest dependencies. Host proc macros
        // and build scripts retain their installed sysroot and Cargo flags.
        if let Some(target) = value("--target") {
            if env.std_target.as_ref() != Some(&target) {
                return Err("standard-library MIR target does not match rustc's target".into());
            }
            if value("--sysroot").is_some_and(|existing| existing != *sysroot) {
                return Err("--std-mir conflicts with an explicit rustc --sysroot".into());
            }
            if value("--sysroot").is_none() {
                args.extend(["--sysroot".into(), sysroot.clone()]);
            }
        }
    }
    let crate_name = args
        .windows(2)
        .find(|a| a[0] == "--crate-name")
        .map(|a| a[1].clone());
    let library = args
        .windows(2)
        .any(|a| a[0] == "--crate-type" && a[1].split(',').any(|t| t == "lib" || t == "rlib"));
    let wrong_package = env
        .export_package
        .as_ref()
        .is_some_and(|p| env.package.as_ref() != Some(p) || !env.primary_package);
    // harness=false targets use cfg(test); adding --test would change expansion.
    let test_compilation = args.iter().any(|a| a == "--test" || a == "--cfg=test")
        || args.windows(2).any(|a| a[0] == "--cfg" && a[1] == "test");
    let wrong_manifest = env.export_manifest.as_ref().is_some_and(|p| {
        env.manifest
            .as_ref()
            .is_none_or(|dir| PathBuf::from(p) != PathBuf::from(dir))
    });
    let export = !wrapper
        || !((env.export_crate.is_none() && env.export_package.is_none())
            || (env.export_crate.is_some() && crate_name != env.export_crate)
            || wrong_package
            || (env.export_package.is_some() && !env.export_test && !library)
            || wrong_manifest
            || (env.export_test && !test_compilation));
    // With the launcher's explicit guest target, Cargo builds host dependencies
    // separately and omits --target on those rustc invocations. They serve host
    // build scripts/proc macros, not guest MIR lookup. Preserve their original
    // flags, including any user-requested MIR encoding. Without that complete
    // context, or for a selected export, retain the conservative old policy.
    let host_only = !export
        && env.std_sysroot.as_ref().is_some_and(|s| !s.is_empty())
        && env.std_target.as_ref().is_some_and(|s| !s.is_empty())
        && !args.iter().any(|arg| arg == "--target" || arg.starts_with("--target="));
    if wrapper && library && !host_only {
        args.push("-Zalways-encode-mir=yes".into());
    }
    Ok(Route {
        args,
        wrapper,
        export,
    })
}
