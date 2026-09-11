use cranelift_codegen::incremental_cache::CacheKvStore;
use rust_interp_function_cache::DiskCache;
use std::borrow::Cow;

pub(crate) struct FunctionCache {
    store: DiskCache,
    pub(crate) hits: u64,
    pub(crate) misses: u64,
    write_errors: u64,
}

impl FunctionCache {
    pub(crate) fn from_env() -> Option<Self> {
        let root = std::env::var_os("RUST_INTERP_FUNCTION_CACHE")?;
        if root.is_empty() {
            return None;
        }
        // Registry dependencies already have durable Cargo artifacts. Avoid
        // populating a finer-grained cache for code the developer won't edit.
        if let Some(scope) = std::env::var_os("RUST_INTERP_CACHE_WORKSPACE") {
            let manifest = std::env::var_os("CARGO_MANIFEST_DIR")?;
            if !std::path::Path::new(&manifest).starts_with(std::path::Path::new(&scope)) {
                return None;
            }
        }
        Some(Self {
            store: DiskCache::new(root),
            hits: 0,
            misses: 0,
            write_errors: 0,
        })
    }
}

impl CacheKvStore for FunctionCache {
    fn get(&self, key: &[u8]) -> Option<Cow<'_, [u8]>> {
        self.store.get(key).map(Cow::Owned)
    }
    fn insert(&mut self, key: &[u8], data: Vec<u8>) {
        if self.store.insert(key, &data).is_err() {
            self.write_errors += 1;
        }
    }
}

impl Drop for FunctionCache {
    fn drop(&mut self) {
        // A fresh path per Cargo invocation avoids counting Cargo-replayed stderr
        // as real cache activity on no-op builds.
        if let Some(path) = std::env::var_os("RUST_INTERP_CACHE_STATS_PATH") {
            use std::io::Write;
            if let Ok(mut file) = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
            {
                // Format first: write_fmt may issue separate writes per field,
                // which interleave between concurrent rustc workers.
                let record = format!(
                    "{} {} {} {}\n",
                    std::process::id(),
                    self.hits,
                    self.misses,
                    self.write_errors
                );
                let _ = file.write_all(record.as_bytes());
            }
        }
        if std::env::var_os("RUST_INTERP_CACHE_STATS").is_some() {
            eprintln!(
                "[function-cache] hits={} misses={} write_errors={}",
                self.hits, self.misses, self.write_errors
            );
        }
    }
}
