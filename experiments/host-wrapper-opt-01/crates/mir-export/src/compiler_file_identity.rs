//! Cheap identity checks for files whose complete bytes were checked at build time.
//! The publication still needs its own complete binary/loader-closure proof.
use std::path::Path;

pub type Stamp = [u64; 8];

#[cfg(unix)]
pub fn stamp(path: &Path) -> Result<Stamp, String> {
    use std::os::unix::fs::MetadataExt;
    if path.to_str().is_none_or(|p| p.contains(['\n', '\r'])) {
        return Err("compiler identity path must be UTF-8 without line separators".into());
    }
    let meta = path.symlink_metadata().map_err(|e| e.to_string())?;
    if !meta.is_file() || path.canonicalize().map_err(|e| e.to_string())? != path {
        return Err(format!("compiler identity requires a canonical ordinary file: {}", path.display()));
    }
    Ok([meta.dev(), meta.ino(), meta.mode() as u64, meta.len(),
        meta.mtime() as u64, meta.mtime_nsec() as u64,
        meta.ctime() as u64, meta.ctime_nsec() as u64])
}

#[cfg(not(unix))]
pub fn stamp(_path: &Path) -> Result<Stamp, String> {
    Err("separate compiler roles currently require Unix file identities".into())
}

pub fn check(path: &Path, expected: Stamp) -> Result<(), String> {
    if stamp(path)? != expected {
        return Err(format!("compiler file identity changed: {}", path.display()));
    }
    Ok(())
}
