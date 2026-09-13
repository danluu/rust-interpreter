//! Build-time opt-in binding. This verifies supplied inputs; it does not assemble
//! or publish a compiler/sysroot, or claim that the private ABI has been qualified.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::process::Command;

#[path = "src/compiler_file_identity.rs"]
pub mod file_identity;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct File {
    pub path: PathBuf,
    pub sha256: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Compiler {
    pub executable: File,
    /// Exact stdout of this executable's -vV, not the other role's version.
    pub verbose_version: String,
    /// Exact canonical default sysroot probed without a --sysroot override.
    pub default_sysroot: PathBuf,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Binding {
    pub schema_version: u32,
    pub policy: String,
    pub build: Compiler,
    pub runtime: Compiler,
    pub runtime_source_commit: String,
    pub runtime_driver: File,
    /// Separate exhaustive ordinary-file inventory of a fresh private sysroot.
    pub private_sysroot_manifest: File,
    /// Exact encoded Cargo rustflags. Normal Cargo dependency flags still apply.
    pub build_rustflags: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PrivateSysroot {
    pub schema_version: u32,
    pub build_compiler_sha256: String,
    pub runtime_source_commit: String,
    pub sysroot: PathBuf,
    pub host: String,
    /// Relative paths of every file, including the beta standard library and
    /// the full successful rustc-private build-stamp closure (not check output).
    pub files: BTreeMap<PathBuf, String>,
}

pub fn digest(bytes: &[u8]) -> String { format!("{:x}", Sha256::digest(bytes)) }

fn require(ok: bool, message: &str) -> Result<(), String> {
    if ok { Ok(()) } else { Err(message.into()) }
}

pub fn field<'a>(version: &'a str, name: &str) -> Result<&'a str, String> {
    let prefix = format!("{name}: ");
    let rows: Vec<_> = version.lines().filter_map(|line| line.strip_prefix(&prefix)).collect();
    require(rows.len() == 1 && !rows[0].is_empty(), "missing or repeated compiler version field")?;
    Ok(rows[0])
}

fn directory(path: &Path) -> Result<(), String> {
    require(path.to_str().is_some_and(|p| !p.contains(['\n', '\r'])), "invalid sysroot path")?;
    require(path.is_absolute() && path.canonicalize().map_err(|e| e.to_string())? == path
        && path.symlink_metadata().map_err(|e| e.to_string())?.is_dir(),
        "compiler sysroot must be a canonical directory")
}

pub fn read_file(file: &File) -> Result<Vec<u8>, String> {
    require(file.sha256.len() == 64 && file.sha256.bytes().all(|b| b.is_ascii_hexdigit()),
        "invalid file SHA-256")?;
    let before = file_identity::stamp(&file.path)?;
    let bytes = std::fs::read(&file.path).map_err(|e| e.to_string())?;
    require(digest(&bytes) == file.sha256, "compiler binding file hash mismatch")?;
    file_identity::check(&file.path, before)?;
    Ok(bytes)
}

fn output(compiler: &Path, args: &[&str]) -> Result<String, String> {
    let result = Command::new(compiler).args(args).output().map_err(|e| e.to_string())?;
    require(result.status.success() && result.stderr.is_empty(), "compiler identity probe failed")?;
    String::from_utf8(result.stdout).map_err(|e| e.to_string())
}

pub fn validate_probe(compiler: &Compiler, version: &str, sysroot: &str) -> Result<(), String> {
    require(version == compiler.verbose_version, "probed compiler version differs from binding")?;
    require(version.lines().next().is_some_and(|s| s.starts_with("rustc ")), "missing actual rustc version header")?;
    require(sysroot.strip_suffix('\n') == compiler.default_sysroot.to_str(),
        "probed compiler default sysroot differs from binding")?;
    let commit = field(version, "commit-hash")?;
    require(commit.len() == 40 && commit.bytes().all(|b| b.is_ascii_hexdigit()),
        "compiler must report its real source commit")?;
    field(version, "host")?;
    Ok(())
}

fn probe(compiler: &Compiler) -> Result<(), String> {
    let stamp = file_identity::stamp(&compiler.executable.path)?;
    read_file(&compiler.executable)?;
    directory(&compiler.default_sysroot)?;
    validate_probe(compiler, &output(&compiler.executable.path, &["-vV"] )?,
        &output(&compiler.executable.path, &["--print", "sysroot"] )?)?;
    file_identity::check(&compiler.executable.path, stamp)
}

pub fn validate_roles(binding: &Binding, private: &PrivateSysroot) -> Result<(), String> {
    require(binding.schema_version == 1 && binding.policy == "separate-compiler-roles-v1"
        && private.schema_version == 1, "unknown compiler-role policy")?;
    require(field(&binding.runtime.verbose_version, "commit-hash")? == binding.runtime_source_commit,
        "runtime source commit differs from actual runtime compiler")?;
    require(private.runtime_source_commit == binding.runtime_source_commit
        && private.build_compiler_sha256 == binding.build.executable.sha256,
        "private metadata closure belongs to different compiler roles")?;
    require(field(&binding.build.verbose_version, "host")? == private.host
        && field(&binding.runtime.verbose_version, "host")? == private.host,
        "build/runtime/private sysroot hosts differ")?;
    require(binding.runtime.executable.path == binding.runtime.default_sysroot.join("bin/rustc"),
        "runtime compiler must be the named sysroot's compiler")?;
    require(binding.runtime_driver.path.parent() == Some(binding.runtime.default_sysroot.join("lib").as_path())
        && binding.runtime_driver.path.file_name().and_then(|v| v.to_str()).is_some_and(|v|
            v.starts_with("librustc_driver-") && (v.ends_with(".dylib") || v.ends_with(".so"))),
        "runtime driver must be the actual compiler's driver library")?;
    require(private.sysroot != binding.runtime.default_sysroot
        && private.sysroot != binding.build.default_sysroot,
        "private build sysroot must be a separate owned composition")?;
    let root = private.sysroot.to_str().ok_or("non-UTF8 private sysroot")?;
    let flags = &binding.build_rustflags;
    require(flags.iter().filter(|v| v.starts_with("--sysroot")).count() == 1
        && flags.iter().any(|v| v == &format!("--sysroot={root}")),
        "private tool flags require one explicit build sysroot")?;
    require(!flags.iter().any(|v| v.starts_with('@')), "response files are not permitted")?;
    let lib = PathBuf::from(format!("lib/rustlib/{}/lib", private.host));
    let metadata = |prefix: &str, extensions: &[&str]| private.files.keys().any(|p| p.parent() == Some(lib.as_path())
        && p.file_name().and_then(|v| v.to_str()).is_some_and(|v| v.starts_with(prefix) && extensions.iter().any(|ext| v.ends_with(ext))));
    require(metadata("librustc_driver-", &[".rmeta"]) && metadata("libstd-", &[".rlib", ".rmeta"]),
        "private closure lacks separate rustc_driver or standard-library metadata")?;
    let driver_name = binding.runtime_driver.path.file_name().ok_or("missing driver name")?;
    require(private.files.get(&lib.join(driver_name)) == Some(&binding.runtime_driver.sha256),
        "private link driver differs from the runtime driver")?;
    Ok(())
}

fn inventory(root: &Path, at: &Path, files: &mut BTreeMap<PathBuf, String>) -> Result<(), String> {
    for entry in std::fs::read_dir(at).map_err(|e| e.to_string())? {
        let path = entry.map_err(|e| e.to_string())?.path();
        let metadata = path.symlink_metadata().map_err(|e| e.to_string())?;
        if metadata.is_dir() {
            directory(&path)?;
            inventory(root, &path, files)?;
        } else {
            let before = file_identity::stamp(&path)?;
            let bytes = std::fs::read(&path).map_err(|e| e.to_string())?;
            file_identity::check(&path, before)?;
            files.insert(path.strip_prefix(root).map_err(|e| e.to_string())?.to_owned(), digest(&bytes));
        }
    }
    Ok(())
}

pub fn check_private_files(private: &PrivateSysroot) -> Result<(), String> {
    directory(&private.sysroot)?;
    let mut actual = BTreeMap::new();
    inventory(&private.sysroot, &private.sysroot, &mut actual)?;
    require(actual == private.files, "private sysroot differs from exhaustive frozen file inventory")
}

pub fn validate_environment(binding: &Binding, rustc: &Path,
    environment: &BTreeMap<String, String>) -> Result<(), String>
{
    require(rustc == binding.build.executable.path, "RUSTC is not the bound build compiler")?;
    for name in ["RUSTC_FORCE_RUSTC_VERSION", "RUSTC_OVERRIDE_VERSION_STRING", "RUSTFLAGS",
        "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER"] {
        require(!environment.contains_key(name), "version overrides, wrappers and alternate RUSTFLAGS are not permitted for separate roles")?;
    }
    require(environment.get("CARGO_ENCODED_RUSTFLAGS") == Some(&binding.build_rustflags.join("\x1f")),
        "actual encoded rustflags differ from the compiler-role binding")?;
    let host = field(&binding.build.verbose_version, "host")?;
    require(environment.get("HOST").map(String::as_str) == Some(host)
        && environment.get("TARGET").map(String::as_str) == Some(host),
        "separate compiler roles require a native host tool build")
}

/// Return checked bytes for embedding and dependencies for Cargo invalidation.
pub fn load(path: &Path, rustc: &Path) -> Result<(Binding, PrivateSysroot, String, [file_identity::Stamp; 2]), String> {
    require(cfg!(any(target_os = "macos", target_os = "linux")),
        "separate compiler roles currently support macOS/Linux driver loading")?;
    let before = file_identity::stamp(path)?;
    let bytes = std::fs::read(path).map_err(|e| e.to_string())?;
    let binding: Binding = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
    let runtime_stamps = [file_identity::stamp(&binding.runtime.executable.path)?,
        file_identity::stamp(&binding.runtime_driver.path)?];
    let private: PrivateSysroot = serde_json::from_slice(&read_file(&binding.private_sysroot_manifest)?)
        .map_err(|e| e.to_string())?;
    let mut env = BTreeMap::new();
    for name in ["RUSTC_FORCE_RUSTC_VERSION", "RUSTC_OVERRIDE_VERSION_STRING", "RUSTFLAGS",
        "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "CARGO_ENCODED_RUSTFLAGS", "HOST", "TARGET"] {
        if let Some(value) = std::env::var_os(name) {
            env.insert(name.to_owned(), value.into_string().map_err(|_| "non-UTF8 compiler-role environment")?);
        }
    }
    validate_environment(&binding, rustc, &env)?;
    validate_roles(&binding, &private)?;
    probe(&binding.build)?;
    probe(&binding.runtime)?;
    read_file(&binding.runtime_driver)?;
    check_private_files(&private)?;
    file_identity::check(&binding.runtime.executable.path, runtime_stamps[0])?;
    file_identity::check(&binding.runtime_driver.path, runtime_stamps[1])?;
    file_identity::check(path, before)?;
    let canonical = serde_json::to_string(&binding).map_err(|e| e.to_string())?;
    Ok((binding, private, canonical, runtime_stamps))
}
