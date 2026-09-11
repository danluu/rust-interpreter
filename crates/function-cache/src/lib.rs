//! Local, disposable backing storage for Cranelift's versioned function stencils.
//! Keys and dependency semantics belong to Cranelift. This layer checks storage
//! integrity and publishes complete entries atomically. I/O failures are misses.
use sha2::{Digest, Sha256};
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

const MAGIC: &[u8; 8] = b"RICACHE1";
const MAX_ENTRY: usize = 64 * 1024 * 1024;
static SERIAL: AtomicU64 = AtomicU64::new(0);

pub struct DiskCache {
    root: PathBuf,
}

impl DiskCache {
    /// The caller supplies a private directory namespaced by backend identity.
    /// This is a trusted local cache, not a format for accepting remote code.
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    fn path(&self, key: &[u8]) -> Option<PathBuf> {
        if key.len() != 32 {
            return None;
        }
        const DIGITS: &[u8; 16] = b"0123456789abcdef";
        let mut bytes = [0; 64];
        for (i, byte) in key.iter().enumerate() {
            bytes[2 * i] = DIGITS[(byte >> 4) as usize];
            bytes[2 * i + 1] = DIGITS[(byte & 15) as usize];
        }
        let hex = std::str::from_utf8(&bytes).expect("hexadecimal digits are UTF-8");
        Some(self.root.join(&hex[..2]).join(&hex[2..]))
    }

    pub fn get(&self, key: &[u8]) -> Option<Vec<u8>> {
        let mut file = fs::File::open(self.path(key)?).ok()?;
        let length = file.metadata().ok()?.len();
        if !(48..=(MAX_ENTRY + 48) as u64).contains(&length) {
            return None;
        }
        let mut header = [0; 48];
        file.read_exact(&mut header).ok()?;
        if &header[..8] != MAGIC {
            return None;
        }
        let size = u64::from_le_bytes(header[8..16].try_into().ok()?);
        if size != length - 48 {
            return None;
        }
        let mut data = vec![0; size as usize];
        file.read_exact(&mut data).ok()?;
        // Bind the payload to its key as well as checking for truncation/bit flips.
        let mut hash = Sha256::new();
        hash.update(key);
        hash.update(&data);
        if hash.finalize().as_slice() != &header[16..48] {
            return None;
        }
        Some(data)
    }

    pub fn insert(&self, key: &[u8], data: &[u8]) -> std::io::Result<()> {
        if data.len() > MAX_ENTRY {
            return Ok(());
        }
        let path = match self.path(key) {
            Some(path) => path,
            None => return Ok(()),
        };
        let parent = path.parent().expect("cache path has parent");
        fs::create_dir_all(parent)?;
        let temporary = parent.join(format!(
            ".tmp-{}-{}",
            std::process::id(),
            SERIAL.fetch_add(1, Ordering::Relaxed)
        ));
        // Never follow/overwrite an existing temporary path.
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        let result = (|| {
            let mut hash = Sha256::new();
            hash.update(key);
            hash.update(data);
            file.write_all(MAGIC)?;
            file.write_all(&(data.len() as u64).to_le_bytes())?;
            file.write_all(&hash.finalize())?;
            file.write_all(data)?;
            // Cache durability across power loss is unnecessary: a bad entry is a miss.
            drop(file);
            fs::rename(&temporary, &path)
        })();
        if result.is_err() {
            let _ = fs::remove_file(&temporary);
        }
        result
    }

    pub fn root(&self) -> &Path {
        &self.root
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Scratch(PathBuf);
    impl Scratch {
        fn new() -> Self {
            let p = std::env::temp_dir().join(format!(
                "rust-interp-cache-test-{}-{}",
                std::process::id(),
                SERIAL.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&p).unwrap();
            Self(p)
        }
    }
    impl Drop for Scratch {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }
    #[test]
    fn survives_restart_and_rejects_corruption_and_wrong_keys() {
        let temp = Scratch::new();
        let key = [1; 32];
        let cache = DiskCache::new(&temp.0);
        cache.insert(&key, b"code").unwrap();
        let restarted = DiskCache::new(&temp.0);
        assert_eq!(restarted.get(&key).unwrap(), b"code");
        assert!(restarted.get(&[2; 32]).is_none());
        let path = cache.path(&key).unwrap();
        let original = fs::read(&path).unwrap();
        let other = cache.path(&[3; 32]).unwrap();
        fs::create_dir_all(other.parent().unwrap()).unwrap();
        fs::write(&other, &original).unwrap();
        assert!(cache.get(&[3; 32]).is_none());
        for n in [0, 8, 47, original.len() - 1] {
            fs::write(&path, &original[..n]).unwrap();
            assert!(cache.get(&key).is_none());
        }
        let mut corrupted = original;
        corrupted[48] ^= 1;
        fs::write(&path, corrupted).unwrap();
        assert!(cache.get(&key).is_none());
        cache.insert(&key, b"repaired").unwrap();
        assert_eq!(cache.get(&key).unwrap(), b"repaired");
    }
    #[test]
    fn concurrent_publication_never_exposes_partial_values() {
        let temp = Scratch::new();
        let cache = std::sync::Arc::new(DiskCache::new(&temp.0));
        let threads: Vec<_> = (0..8)
            .map(|i| {
                let cache = cache.clone();
                std::thread::spawn(move || {
                    let data = vec![i; 8192];
                    for _ in 0..30 {
                        cache.insert(&[7; 32], &data).unwrap();
                        let read = cache.get(&[7; 32]).unwrap();
                        assert_eq!(read.len(), 8192);
                        assert!(read.iter().all(|b| *b == read[0]));
                    }
                })
            })
            .collect();
        for t in threads {
            t.join().unwrap();
        }
    }
    #[test]
    fn unavailable_storage_is_a_miss() {
        let temp = Scratch::new();
        let path = temp.0.join("file");
        fs::write(&path, b"not a directory").unwrap();
        let cache = DiskCache::new(path);
        assert!(cache.get(&[0; 32]).is_none());
        assert!(cache.insert(&[0; 32], b"code").is_err());
        assert!(cache.get(b"../invalid").is_none());
    }
}
