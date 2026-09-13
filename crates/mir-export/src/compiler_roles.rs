//! Runtime checks for the explicit, already byte-verified build-time binding.
//! No compiler probe subprocess or full driver rehash is added to each export.
#[path = "compiler_file_identity.rs"]
mod file_identity;
use std::path::{Path, PathBuf};

pub struct Runtime {
    pub compiler: &'static str,
    pub driver: &'static str,
    pub sysroot: &'static str,
    pub version: &'static str,
    pub compiler_stamp: file_identity::Stamp,
    pub driver_stamp: file_identity::Stamp,
}

include!(concat!(env!("OUT_DIR"), "/compiler_roles.rs"));

/// The wrapper is intentionally std-only and does not load rustc_driver.
pub fn check_files() -> Result<(), String> {
    let Some(runtime) = RUNTIME.as_ref() else { return Ok(()); };
    let overridden = ["RUSTC_FORCE_RUSTC_VERSION", "RUSTC_OVERRIDE_VERSION_STRING"]
        .iter().any(|name| std::env::var_os(name).is_some());
    check_binding(Some(runtime), overridden)
}

pub fn check_binding(runtime: Option<&Runtime>, overridden: bool) -> Result<(), String> {
    if let Some(runtime) = runtime {
        if overridden {
            return Err("compiler version overrides are incompatible with bound compiler roles".into());
        }
        validate_files(runtime)?;
    }
    Ok(())
}

fn validate_files(runtime: &Runtime) -> Result<(), String> {
    file_identity::check(Path::new(runtime.compiler), runtime.compiler_stamp)?;
    file_identity::check(Path::new(runtime.driver), runtime.driver_stamp)?;
    if Path::new(runtime.sysroot).canonicalize().map_err(|e| e.to_string())? != Path::new(runtime.sysroot) {
        return Err("runtime sysroot identity changed".into());
    }
    Ok(())
}

#[allow(dead_code, reason = "the std-only wrapper checks files without loading rustc_driver")]
pub fn validate_loaded(runtime: &Runtime, version: Option<&str>, driver: &Path) -> Result<(), String> {
    if version != Some(runtime.version) {
        return Err("linked compiler version differs from the probed runtime compiler".into());
    }
    if driver.canonicalize().map_err(|e| e.to_string())? != Path::new(runtime.driver) {
        return Err("loaded rustc_driver differs from the bound runtime library".into());
    }
    validate_files(runtime)
}

/// Resolve a function supplied by rustc_driver, not a function in the exporter.
/// This detects a different dylib selected through a loader search override.
#[cfg(any(target_os = "macos", target_os = "linux"))]
#[allow(dead_code, reason = "driver image discovery runs only in the exporter")]
pub fn loaded_driver(function: *const ()) -> Result<PathBuf, String> {
    use std::ffi::{CStr, c_char, c_int, c_void};
    #[repr(C)]
    struct DlInfo {
        filename: *const c_char,
        base: *mut c_void,
        symbol: *const c_char,
        address: *mut c_void,
    }
    #[cfg_attr(target_os = "linux", link(name = "dl"))]
    unsafe extern "C" { fn dladdr(address: *const c_void, info: *mut DlInfo) -> c_int; }
    let mut info = DlInfo { filename: std::ptr::null(), base: std::ptr::null_mut(),
        symbol: std::ptr::null(), address: std::ptr::null_mut() };
    // dladdr writes the complete Dl_info on success; dli_fname belongs to the
    // loaded image, whose lifetime spans this call and the following copy.
    if unsafe { dladdr(function.cast(), &mut info) } == 0 || info.filename.is_null() {
        return Err("cannot identify loaded rustc_driver".into());
    }
    use std::os::unix::ffi::OsStrExt;
    let bytes = unsafe { CStr::from_ptr(info.filename) }.to_bytes();
    Ok(PathBuf::from(std::ffi::OsStr::from_bytes(bytes)))
}

#[cfg(not(any(target_os = "macos", target_os = "linux")))]
#[allow(dead_code, reason = "driver image discovery runs only in the exporter")]
pub fn loaded_driver(_function: *const ()) -> Result<PathBuf, String> {
    Err("separate compiler roles require supported driver-image discovery".into())
}
