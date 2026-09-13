//! Pinned rustc incremental framing, independent of compiler-owned values.
use std::path::{Path, PathBuf};

pub const NAMESPACE: &str = ".rust-interp-query-demand-v1";

pub fn incremental_directory(original: &Path) -> PathBuf {
    original.join(NAMESPACE)
}

/// Matches rustc_incremental::persist::file_format::write_file_header in
/// nightly-2026-09-08, revision cea272fa356e94bd2ee2cadf376630aa0683867a.
/// The stock OnDiskCache serializer writes everything after this header.
pub fn header(version: &str) -> Result<Vec<u8>, &'static str> {
    let length =
        u8::try_from(version.len()).map_err(|_| "compiler cache version exceeds 255 bytes")?;
    let mut bytes = Vec::with_capacity(7 + version.len());
    bytes.extend_from_slice(b"RSIC");
    bytes.extend_from_slice(&0u16.to_le_bytes());
    bytes.push(length);
    bytes.extend_from_slice(version.as_bytes());
    Ok(bytes)
}
