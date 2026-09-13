//! Versioned, bounded evidence sidecars in rustc's existing incremental session.
//! Shares v1's fresh-inode COW discipline; stores no executable HIR payload.
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::hash::Hash;
use rustc_data_structures::{fingerprint::Fingerprint, stable_hash::StableHasher};
use serde::{Deserialize, Serialize};
use super::{FORMAT, journal::Journal};

pub(super) const MAX_RECORD: usize = 4 * 1024 * 1024;
static NEXT: AtomicU64 = AtomicU64::new(0);

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Record { format: String, key: Vec<u8>, journal: Journal, checksum: String }

fn checksum(key: &[u8], journal: &Journal) -> Option<String> {
    let bytes = serde_json::to_vec(journal).ok()?;
    if bytes.len() > MAX_RECORD { return None; }
    let mut state = StableHasher::new();
    key.hash(&mut state); bytes.hash(&mut state);
    let fingerprint: Fingerprint = state.finish();
    Some(super::hex(fingerprint))
}

pub(super) fn read(path: &Path, key: &[u8]) -> Option<Journal> {
    if !fs::symlink_metadata(path).ok()?.is_file() { return None; }
    let file = File::open(path).ok()?;
    let metadata = file.metadata().ok()?;
    if !metadata.is_file() || metadata.len() > MAX_RECORD as u64 { return None; }
    let mut bytes = Vec::new();
    file.take(MAX_RECORD as u64 + 1).read_to_end(&mut bytes).ok()?;
    if bytes.len() > MAX_RECORD { return None; }
    let record: Record = serde_json::from_slice(&bytes).ok()?;
    if record.format != FORMAT || record.key != key || record.checksum != checksum(key, &record.journal)? {
        return None;
    }
    Some(record.journal)
}

pub(super) fn write(path: &Path, key: &[u8], journal: &Journal) -> bool {
    let Some(checksum) = checksum(key, journal) else { return false; };
    let record = Record { format: FORMAT.to_owned(), key: key.to_vec(), journal: journal.clone(), checksum };
    let Ok(bytes) = serde_json::to_vec(&record) else { return false; };
    if bytes.len() > MAX_RECORD { return false; }
    let temp = path.with_extension(format!("part-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
    let Ok(mut file) = OpenOptions::new().create_new(true).write(true).open(&temp) else { return false; };
    let result = file.write_all(&bytes);
    drop(file);
    let result = result.and_then(|()| fs::rename(&temp, path));
    if result.is_err() { let _ = fs::remove_file(&temp); }
    result.is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn corrupt_truncated_wrong_key_and_hardlinked_old_inode() {
        let directory = std::env::temp_dir().join(format!("hir-body-journal-{}-{}",
            std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
        fs::create_dir(&directory).unwrap();
        let path = directory.join("current.json"); let old = directory.join("old.json");
        let journal = Journal { events: vec![super::super::journal::Event::Allocate {
            source: super::super::journal::Allocation::Synthetic, relative: 0 }], end_delta: 1, root_relative: 0 };
        assert!(write(&path, b"key", &journal));
        let bytes = fs::read(&path).unwrap(); fs::hard_link(&path, &old).unwrap();
        assert!(write(&path, b"new-key", &journal));
        assert_eq!(fs::read(&old).unwrap(), bytes);
        assert!(read(&path, b"key").is_none()); assert!(read(&old, b"key").is_some());
        for bad in [b"{".to_vec(), b"[]".to_vec(), bytes[..bytes.len()/2].to_vec(), vec![0; MAX_RECORD + 1]] {
            fs::write(&path, bad).unwrap(); assert!(read(&path, b"key").is_none());
        }
        let mut record: Record = serde_json::from_slice(&bytes).unwrap();
        record.journal.end_delta = 2;
        fs::write(&path, serde_json::to_vec(&record).unwrap()).unwrap();
        assert!(read(&path, b"key").is_none());
        fs::remove_dir_all(directory).unwrap();
    }
}
