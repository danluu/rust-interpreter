mod build_compiler_roles;

fn main() {
    use std::path::PathBuf;
    println!("cargo:rerun-if-env-changed=RUSTC");
    println!("cargo:rerun-if-env-changed=RUST_INTERP_COMPILER_ROLES");
    let generated = PathBuf::from(std::env::var_os("OUT_DIR").expect("OUT_DIR"))
        .join("compiler_roles.rs");
    let rustc = std::env::var_os("RUSTC").unwrap_or_else(|| "rustc".into());
    if let Some(path) = std::env::var_os("RUST_INTERP_COMPILER_ROLES") {
        let (binding, private, json, stamps) = build_compiler_roles::load(
            &PathBuf::from(&path), &PathBuf::from(&rustc))
            .unwrap_or_else(|error| panic!("invalid separate compiler roles: {error}"));
        for name in ["RUSTC_FORCE_RUSTC_VERSION", "RUSTC_OVERRIDE_VERSION_STRING", "RUSTFLAGS",
            "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "CARGO_ENCODED_RUSTFLAGS"] {
            println!("cargo:rerun-if-env-changed={name}");
        }
        for path in [PathBuf::from(path), binding.private_sysroot_manifest.path.clone(),
            binding.build.executable.path.clone(), binding.runtime.executable.path.clone(),
            binding.runtime_driver.path.clone(), private.sysroot.clone()] {
            println!("cargo:rerun-if-changed={}", path.display());
        }
        for path in private.files.keys() {
            println!("cargo:rerun-if-changed={}", private.sysroot.join(path).display());
        }
        let sysroot = binding.runtime.default_sysroot.to_str().expect("UTF-8 runtime sysroot");
        let compiler = binding.runtime.executable.path.to_str().expect("UTF-8 runtime compiler");
        let driver = binding.runtime_driver.path.to_str().expect("UTF-8 runtime driver");
        assert!(![sysroot, compiler, driver].iter().any(|v| v.contains(['\n', '\r', ','])),
            "compiler paths cannot contain Cargo/linker control separators");
        let version = binding.runtime.verbose_version.lines().next().expect("runtime version")
            .strip_prefix("rustc ").expect("actual rustc version header");
        println!("cargo:rustc-link-arg=-Wl,-rpath,{sysroot}/lib");
        println!("cargo:rustc-env=RUST_INTERP_SYSROOT={sysroot}");
        println!("cargo:rustc-env=RUST_INTERP_RUNTIME_COMPILER={compiler}");
        println!("cargo:rustc-env=RUST_INTERP_RUSTC_COMMIT={}", binding.runtime_source_commit);
        std::fs::write(generated, format!(
            "pub const BINDING_JSON: Option<&str> = Some({json:?});\n\
             pub const RUNTIME: Option<Runtime> = Some(Runtime {{ compiler: {compiler:?}, driver: {driver:?},\n\
             sysroot: {sysroot:?}, version: {version:?}, compiler_stamp: {:?}, driver_stamp: {:?} }});\n",
            stamps[0], stamps[1])).expect("write compiler roles");
        return;
    }
    // Preserve the original same-toolchain behavior when the opt-in is absent.
    std::fs::write(generated,
        "pub const BINDING_JSON: Option<&str> = None;\npub const RUNTIME: Option<Runtime> = None;\n")
        .expect("write default compiler roles");
    let output = std::process::Command::new(&rustc)
        .args(["--print", "sysroot"])
        .output()
        .expect("rustc sysroot");
    assert!(output.status.success());
    let sysroot = String::from_utf8(output.stdout).expect("UTF-8 sysroot");
    println!("cargo:rustc-link-arg=-Wl,-rpath,{}/lib", sysroot.trim());
    println!("cargo:rustc-env=RUST_INTERP_SYSROOT={}", sysroot.trim());
    println!("cargo:rustc-env=RUST_INTERP_RUNTIME_COMPILER={}/bin/rustc{}",
        sysroot.trim(), std::env::consts::EXE_SUFFIX);
    let version = std::process::Command::new(&rustc)
        .arg("-vV")
        .output()
        .expect("rustc version");
    assert!(version.status.success());
    let version = String::from_utf8(version.stdout).expect("UTF-8 rustc version");
    let commit = version
        .lines()
        .find_map(|line| line.strip_prefix("commit-hash: "))
        .filter(|hash| hash.len() == 40 && hash.bytes().all(|byte| byte.is_ascii_hexdigit()))
        .unwrap_or("unknown");
    println!("cargo:rustc-env=RUST_INTERP_RUSTC_COMMIT={commit}");
}
