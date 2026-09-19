//! Pure binding/identity controls. No rustc subprocess, compiler build or loader
//! compatibility claim is made by these tests.
#[allow(dead_code)]
#[path = "../build_compiler_roles.rs"]
mod build;
#[allow(dead_code)]
#[path = "../src/compiler_roles.rs"]
mod runtime;
#[allow(dead_code)]
#[path = "../src/wrapper_route.rs"]
mod wrapper_route;
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let root = std::env::temp_dir().canonicalize().unwrap().join(format!(
            "rust-interp-role-tests-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
        std::fs::create_dir(&root).unwrap();
        Self(root)
    }
    fn file(&self, name: &str, bytes: &[u8]) -> PathBuf {
        let path = self.0.join(name);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, bytes).unwrap();
        path
    }
}
impl Drop for Temp { fn drop(&mut self) { std::fs::remove_dir_all(&self.0).unwrap(); } }

fn version(commit: &str) -> String {
    format!("rustc 1.100.0-dev\nbinary: rustc\ncommit-hash: {commit}\nhost: aarch64-apple-darwin\n")
}

fn fixture() -> (build::Binding, build::PrivateSysroot) {
    let build_hash = "a".repeat(64);
    let driver_hash = "b".repeat(64);
    let source_commit = "c".repeat(40);
    let host = "aarch64-apple-darwin";
    let target_lib = format!("lib/rustlib/{host}/lib");
    let private = build::PrivateSysroot {
        schema_version: 1, build_compiler_sha256: build_hash.clone(),
        runtime_source_commit: source_commit.clone(), sysroot: "/private-build".into(),
        host: host.into(), files: BTreeMap::from([
            (format!("{target_lib}/libstd-beta.rlib").into(), "d".repeat(64)),
            (format!("{target_lib}/librustc_driver-next.rmeta").into(), "e".repeat(64)),
            (format!("{target_lib}/librustc_driver-next.dylib").into(), driver_hash.clone()),
        ]),
    };
    let binding = build::Binding {
        schema_version: 1, policy: "separate-compiler-roles-v1".into(),
        build: build::Compiler { executable: build::File { path: "/beta/bin/rustc".into(), sha256: build_hash },
            verbose_version: version(&"f".repeat(40)), default_sysroot: "/beta".into() },
        runtime: build::Compiler { executable: build::File { path: "/frontend/bin/rustc".into(), sha256: "1".repeat(64) },
            verbose_version: version(&source_commit), default_sysroot: "/frontend".into() },
        runtime_source_commit: source_commit,
        runtime_driver: build::File { path: "/frontend/lib/librustc_driver-next.dylib".into(), sha256: driver_hash },
        private_sysroot_manifest: build::File { path: "/private.json".into(), sha256: "2".repeat(64) },
        build_rustflags: vec!["--sysroot=/private-build".into()],
    };
    (binding, private)
}

#[test]
fn separate_roles_accept_real_distinct_commits_and_reject_crossed_bindings() {
    let (binding, private) = fixture();
    build::validate_roles(&binding, &private).unwrap();
    let mut bad = binding.clone();
    bad.runtime_source_commit = build::field(&bad.build.verbose_version, "commit-hash").unwrap().into();
    assert!(build::validate_roles(&bad, &private).is_err());
    let mut bad = private.clone();
    bad.build_compiler_sha256 = binding.runtime.executable.sha256.clone();
    assert!(build::validate_roles(&binding, &bad).is_err());
    let mut bad = private.clone();
    bad.runtime_source_commit = "0".repeat(40);
    assert!(build::validate_roles(&binding, &bad).is_err());
    let mut bad = private.clone();
    bad.host = "x86_64-unknown-linux-gnu".into();
    assert!(build::validate_roles(&binding, &bad).is_err());
    let mut bad = private.clone();
    *bad.files.get_mut(Path::new("lib/rustlib/aarch64-apple-darwin/lib/librustc_driver-next.dylib")).unwrap() = "0".repeat(64);
    assert!(build::validate_roles(&binding, &bad).is_err());
}

#[test]
fn actual_probe_must_match_named_role_without_version_substitution() {
    let (binding, _) = fixture();
    build::validate_probe(&binding.runtime, &binding.runtime.verbose_version, "/frontend\n").unwrap();
    assert!(build::validate_probe(&binding.runtime, &binding.build.verbose_version, "/frontend\n").is_err());
    assert!(build::validate_probe(&binding.runtime, &binding.runtime.verbose_version, "/beta\n").is_err());
    let mut malformed = binding.runtime.clone();
    malformed.verbose_version.push_str(&format!("commit-hash: {}\n", "0".repeat(40)));
    assert!(build::validate_probe(&malformed, &malformed.verbose_version, "/frontend\n").is_err());
}

#[test]
fn build_environment_rejects_wrong_compiler_flags_and_even_empty_overrides() {
    let (binding, _) = fixture();
    let env = BTreeMap::from([("CARGO_ENCODED_RUSTFLAGS".into(), binding.build_rustflags.join("\x1f")),
        ("HOST".into(), "aarch64-apple-darwin".into()), ("TARGET".into(), "aarch64-apple-darwin".into())]);
    build::validate_environment(&binding, &binding.build.executable.path, &env).unwrap();
    assert!(build::validate_environment(&binding, &binding.runtime.executable.path, &env).is_err());
    assert!(build::validate_environment(&binding, &binding.build.executable.path, &BTreeMap::new()).is_err());
    for name in ["RUSTC_FORCE_RUSTC_VERSION", "RUSTC_OVERRIDE_VERSION_STRING", "RUSTFLAGS", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER"] {
        for value in ["", "different"] {
            let mut bad = env.clone(); bad.insert(name.into(), value.into());
            assert!(build::validate_environment(&binding, &binding.build.executable.path, &bad).is_err(), "{name}");
        }
    }
}

#[test]
fn private_build_sysroot_cannot_be_overridden() {
    let (binding, private) = fixture();
    for extra in [vec!["--sysroot=/frontend"], vec!["--sysroot", "/frontend"], vec!["@flags"]] {
        let mut bad = binding.clone(); bad.build_rustflags.extend(extra.into_iter().map(str::to_owned));
        assert!(build::validate_roles(&bad, &private).is_err());
    }
    let mut bad = private.clone(); bad.sysroot = binding.runtime.default_sysroot.clone();
    assert!(build::validate_roles(&binding, &bad).is_err());
    let mut bad = private.clone(); bad.sysroot = binding.build.default_sysroot.clone();
    assert!(build::validate_roles(&binding, &bad).is_err());
}

#[test]
fn exhaustive_private_files_reject_missing_corrupt_extra_and_symlink_inputs() {
    let temp = Temp::new();
    let file = temp.file("lib/private.rmeta", b"private metadata");
    let (_, mut private) = fixture();
    private.sysroot = temp.0.clone();
    private.files = BTreeMap::from([("lib/private.rmeta".into(), build::digest(b"private metadata"))]);
    build::check_private_files(&private).unwrap();
    std::fs::write(&file, b"different metadata").unwrap();
    assert!(build::check_private_files(&private).is_err());
    std::fs::write(&file, b"private metadata").unwrap();
    let extra = temp.file("extra.rmeta", b"unexpected compiler input");
    assert!(build::check_private_files(&private).is_err());
    std::fs::remove_file(extra).unwrap();
    std::fs::remove_file(&file).unwrap();
    assert!(build::check_private_files(&private).is_err());
    #[cfg(unix)] {
        let outside = Temp::new(); let target = outside.file("metadata", b"private metadata");
        std::os::unix::fs::symlink(target, &file).unwrap();
        assert!(build::check_private_files(&private).is_err());
    }
}

#[test]
fn binding_file_hash_and_schema_are_enforced() {
    let temp = Temp::new();
    let path = temp.file("binding.json", b"frozen binding");
    let mut file = build::File { path, sha256: build::digest(b"frozen binding") };
    assert_eq!(build::read_file(&file).unwrap(), b"frozen binding");
    file.sha256 = build::digest(b"other");
    assert!(build::read_file(&file).is_err());
    let (binding, _) = fixture();
    let mut json = serde_json::to_value(&binding).unwrap();
    json["claimed_qualified"] = true.into();
    assert!(serde_json::from_value::<build::Binding>(json).is_err());
}

#[test]
fn runtime_default_and_loaded_image_checks_preserve_distinct_roles() {
    // The default behavior adds no role-specific version-override restriction.
    runtime::check_binding(None, true).unwrap();
    let temp = Temp::new();
    let compiler = temp.file("bin/rustc", b"runtime compiler");
    let driver = temp.file("lib/librustc_driver-real.dylib", b"runtime driver");
    let foreign = temp.file("lib/librustc_driver-foreign.dylib", b"same version, other code");
    let runtime = runtime::Runtime {
        compiler: Box::leak(compiler.to_str().unwrap().to_owned().into_boxed_str()),
        driver: Box::leak(driver.to_str().unwrap().to_owned().into_boxed_str()),
        sysroot: Box::leak(temp.0.to_str().unwrap().to_owned().into_boxed_str()),
        version: "actual embedded version",
        compiler_stamp: build::file_identity::stamp(&compiler).unwrap(),
        driver_stamp: build::file_identity::stamp(&driver).unwrap(),
    };
    runtime::check_binding(Some(&runtime), false).unwrap();
    assert!(runtime::check_binding(Some(&runtime), true).is_err());
    runtime::validate_loaded(&runtime, Some("actual embedded version"), &driver).unwrap();
    assert!(runtime::validate_loaded(&runtime, Some("beta build version"), &driver).is_err());
    assert!(runtime::validate_loaded(&runtime, Some("actual embedded version"), &foreign).is_err());
    std::fs::write(&driver, b"replaced runtime driver bytes").unwrap();
    assert!(runtime::validate_loaded(&runtime, Some("actual embedded version"), &driver).is_err());
}

#[test]
fn exporter_route_requires_runtime_compiler_and_rejects_build_compiler() {
    let temp = Temp::new();
    let compiler = temp.file("runtime/bin/rustc", b"runtime");
    let build = temp.file("build/bin/rustc", b"build");
    let mut route = wrapper_route::Route { args: vec![compiler.to_str().unwrap().into()],
        wrapper: true, export: true, borrowck_cache: wrapper_route::BorrowckCacheMode::Off,
        custom_compiler: false, host_proc_macro_opt: false, host_library_opt: false, host_codegen_opt: false };
    route.check_compiler(&temp.0.join("runtime")).unwrap();
    route.args[0] = build.to_str().unwrap().into();
    assert!(route.check_compiler(&temp.0.join("runtime")).is_err());
}
