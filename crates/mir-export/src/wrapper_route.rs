//! Cargo invocation routing shared by the standalone exporter and light wrapper.
//! Keep this module independent of rustc_driver and of exporter dependencies.
use std::ffi::{OsStr, OsString};
use std::path::{Path, PathBuf};

pub fn frontend_worker_capability() -> String {
    format!(
        r#"{{"schema_version":1,"policy":"frontend-workers-v1","counts":[1,2],"flag":"-Zthreads","compiler_commit":"{}"}}"#,
        option_env!("RUST_INTERP_RUSTC_COMMIT").unwrap_or("unknown"),
    )
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum BorrowckCacheMode {
    #[default]
    Off,
    Verify,
    Reuse,
}

impl BorrowckCacheMode {
    /// An explicit input keeps environment validation identical in both tools
    /// and lets route tests avoid mutating the process environment.
    pub fn parse(value: Option<&OsStr>) -> Result<Self, String> {
        match value.map(OsStr::to_str) {
            None | Some(Some("off")) => Ok(Self::Off),
            Some(Some("verify")) => Ok(Self::Verify),
            Some(Some("reuse")) => Ok(Self::Reuse),
            _ => Err("RUST_INTERP_BORROWCK_CACHE must be off, verify, or reuse".into()),
        }
    }
}

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
    pub borrowck_cache: Option<OsString>,
    pub frontend_workers: Option<OsString>,
    pub frontend_compiler: Option<OsString>,
    pub conflicting_frontend_policy: bool,
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
            borrowck_cache: std::env::var_os("RUST_INTERP_BORROWCK_CACHE"),
            frontend_workers: std::env::var_os("RUST_INTERP_FRONTEND_WORKERS"),
            frontend_compiler: option_env!("RUST_INTERP_SYSROOT").map(|root| {
                Path::new(root)
                    .join(format!("bin/rustc{}", std::env::consts::EXE_SUFFIX))
                    .into_os_string()
            }),
            conflicting_frontend_policy: std::env::var_os("RUST_INTERP_COMPILER_RUSTC").is_some()
                || ["RUST_INTERP_STABLE_CGU_PARTITIONING", "RUST_INTERP_HOST_PROC_MACRO_OPT"]
                    .iter().any(|name| std::env::var_os(name).is_some_and(|value| value != "off")),
        }
    }
}

pub struct Route {
    /// Real compiler argv in wrapper mode, original argv in standalone mode.
    pub args: Vec<String>,
    pub wrapper: bool,
    pub export: bool,
    pub borrowck_cache: BorrowckCacheMode,
}

impl Route {
    pub fn requires_exporter(&self) -> bool {
        self.export || borrowck_driver_required(&self.args, self.borrowck_cache)
    }
}

/// Only bypass the driver for a narrow grammar of Cargo's metadata probes.
/// Cargo can include stdin and a crate name in these queries. Unknown options,
/// source paths and response files conservatively retain cache callbacks.
pub fn borrowck_driver_required(args: &[String], mode: BorrowckCacheMode) -> bool {
    if mode == BorrowckCacheMode::Off {
        return false;
    }
    // Keep this list deliberately narrow. In particular, link-args and
    // native-static-libs are compilation outputs, not informational probes.
    let metadata_print = |value: &str| {
        matches!(value, "cfg" | "sysroot" | "target-list" | "target-libdir" |
            "file-names" | "crate-name" | "split-debuginfo" | "host-tuple")
    };
    let mut args = args.iter().skip(1);
    let mut query = false;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "-vV" | "-V" | "--version" | "-h" | "--help" => query = true,
            "--print" => {
                if !args.next().is_some_and(|value| metadata_print(value)) {
                    return true;
                }
                query = true;
            }
            "--crate-name" | "--crate-type" | "--target" | "--sysroot" => {
                // Consume values before scanning for queries. An option value
                // resembling --print must never suppress a real compilation.
                if args.next().is_none() {
                    return true;
                }
            }
            "-" | "-Zalways-encode-mir=yes" => {}
            _ => {
                if let Some(value) = arg.strip_prefix("--print=") {
                    if !metadata_print(value) {
                        return true;
                    }
                    query = true;
                } else if !["--crate-name=", "--crate-type=", "--target=", "--sysroot="]
                    .iter().any(|prefix| arg.starts_with(prefix)) {
                    return true;
                }
            }
        }
    }
    !query
}

pub fn route(mut args: Vec<String>, env: &Environment) -> Result<Route, String> {
    let borrowck_cache = BorrowckCacheMode::parse(env.borrowck_cache.as_deref())?;
    // Preserve the existing wrapper convention, including standalone exports.
    let wrapper = args
        .get(1)
        .is_some_and(|s| Path::new(s).file_stem().is_some_and(|s| s == "rustc"));
    if wrapper {
        args.remove(0);
    }
    if let Some(workers) = &env.frontend_workers {
        if !matches!(workers.to_str(), Some("1" | "2")) {
            return Err("RUST_INTERP_FRONTEND_WORKERS must be 1 or 2".into());
        }
        if !wrapper || env.frontend_compiler.as_deref() != Some(OsStr::new(&args[0])) {
            return Err("frontend workers require Cargo's pinned rustc executable".into());
        }
        if env.conflicting_frontend_policy || borrowck_cache != BorrowckCacheMode::Off {
            return Err("frontend workers cannot be combined with another compiler, macro, or borrowck policy".into());
        }
        for (index, arg) in args.iter().enumerate().skip(1) {
            let zoption = if arg == "-Z" {
                args.get(index + 1).map(String::as_str)
            } else {
                arg.strip_prefix("-Z")
            };
            let zname = zoption.map(|value| value.split('=').next().unwrap().replace('_', "-"));
            if arg.starts_with('@') || arg == "--jobs" || arg.starts_with("--jobs=")
                || arg.starts_with("-j") || arg == "--jobs-frontend"
                || arg.starts_with("--jobs-frontend=")
                || matches!(zname.as_deref(), Some("threads" | "stable-cgu-partitioning"
                    | "stable-mono-cgu-partitioning" | "proc-macro-execution-strategy"))
            {
                return Err("frontend worker policy conflicts with a compiler flag or response file".into());
            }
        }
        args.push(format!("-Zthreads={}", workers.to_str().unwrap()));
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
    if wrapper && library {
        // Retain the qualified dependency MIR policy, including flag precedence.
        args.push("-Zalways-encode-mir=yes".into());
    }
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
    Ok(Route {
        args,
        wrapper,
        export,
        borrowck_cache,
    })
}
