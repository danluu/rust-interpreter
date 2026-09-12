//! Bounded owned payloads staged in rustc's current incremental session.
use bincode::Options;
use rustc_middle::ty::TyCtxt;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const MAGIC: &[u8; 8] = b"RIFNC001";
const HEADER: usize = 72;
const MAX_FILE: u64 = 128 * 1024 * 1024;
const MAX_PAYLOAD: usize = 64 * 1024 * 1024;
type Result<T> = std::result::Result<T, String>;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Mode { Off, Verify, Reuse, Auto }
pub(crate) fn mode() -> Result<Mode> {
    match std::env::var_os("RUST_INTERP_FUNCTION_CACHE") {
        None => Ok(Mode::Off),
        Some(value) if value == "0" => Ok(Mode::Off),
        Some(value) if value == "verify" => Ok(Mode::Verify),
        Some(value) if value == "reuse" => Ok(Mode::Reuse),
        Some(value) if value == "auto" => Ok(Mode::Auto),
        _ => Err("RUST_INTERP_FUNCTION_CACHE accepts only 0, verify, reuse or auto".into()),
    }
}

pub(crate) fn effective_mode(requested: Mode, incremental_session: bool, dependency_tracking: bool) -> Mode {
    match requested {
        Mode::Auto if incremental_session && dependency_tracking => Mode::Reuse,
        Mode::Auto => Mode::Off,
        mode => mode,
    }
}

#[derive(Serialize, Deserialize)]
struct Entry { node: String, #[serde(with = "payload_bytes")] payload: Vec<u8> }
#[derive(Serialize)]
struct BorrowedEntry<'a> { node: &'a str, #[serde(serialize_with = "payload_bytes::serialize")] payload: &'a [u8] }

// Bincode's fixed-width byte sequence and byte-buffer representations are
// identical. Ask for bulk bytes explicitly instead of visiting every u8.
mod payload_bytes {
    use serde::{Deserializer, Serializer, de::Visitor};
    pub fn serialize<S: Serializer>(bytes: &[u8], serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_bytes(bytes)
    }
    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<Vec<u8>, D::Error> {
        struct Bytes;
        impl<'de> Visitor<'de> for Bytes {
            type Value = Vec<u8>;
            fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result { f.write_str("owned function bytes") }
            fn visit_byte_buf<E: serde::de::Error>(self, bytes: Vec<u8>) -> Result<Self::Value, E> { Ok(bytes) }
            fn visit_bytes<E: serde::de::Error>(self, bytes: &[u8]) -> Result<Self::Value, E> { Ok(bytes.to_vec()) }
        }
        deserializer.deserialize_byte_buf(Bytes)
    }
}

fn valid_node(node: &str) -> bool {
    let Some((a, b)) = node.split_once('-') else { return false; };
    [a, b].iter().all(|part| !part.is_empty() && part.len() <= 16
        && part.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)))
}
fn decode_measured(bytes: &[u8], namespace: &[u8; 32]) -> Result<(HashMap<String, Vec<u8>>, f64)> {
    if bytes.len() < HEADER || bytes.len() as u64 > MAX_FILE || &bytes[..8] != MAGIC {
        return Err("cache file bounds or magic".into());
    }
    if &bytes[8..40] != namespace { return Err("cache namespace changed".into()); }
    let body = &bytes[HEADER..];
    let hash_start = Instant::now();
    if Sha256::digest(body).as_slice() != &bytes[40..HEADER] { return Err("cache integrity check".into()); }
    let hash_seconds = hash_start.elapsed().as_secs_f64();
    let entries: Vec<Entry> = bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(MAX_FILE).reject_trailing_bytes().deserialize(body).map_err(|e| e.to_string())?;
    if entries.len() > 10_000 { return Err("cache entry count".into()); }
    let mut result = HashMap::with_capacity(entries.len());
    for entry in entries {
        if !valid_node(&entry.node) || entry.payload.len() > MAX_PAYLOAD
            || result.insert(entry.node, entry.payload).is_some() {
            return Err("invalid or duplicate cache entry".into());
        }
    }
    Ok((result, hash_seconds))
}
fn encode_measured(entries: &BTreeMap<String, Vec<u8>>, namespace: &[u8; 32]) -> Result<(Vec<u8>, f64)> {
    if entries.len() > 10_000 || entries.iter().any(|(key, value)| !valid_node(key) || value.len() > MAX_PAYLOAD) {
        return Err("cache output bounds".into());
    }
    let values: Vec<_> = entries.iter().map(|(node, payload)| BorrowedEntry { node, payload }).collect();
    let body = bincode::DefaultOptions::new().with_fixint_encoding().with_limit(MAX_FILE - HEADER as u64)
        .serialize(&values).map_err(|e| e.to_string())?;
    let mut bytes = Vec::with_capacity(HEADER + body.len());
    bytes.extend_from_slice(MAGIC);
    bytes.extend_from_slice(namespace);
    let hash_start = Instant::now();
    bytes.extend_from_slice(&Sha256::digest(&body));
    let hash_seconds = hash_start.elapsed().as_secs_f64();
    bytes.extend_from_slice(&body);
    Ok((bytes, hash_seconds))
}
#[cfg(test)]
fn encode(entries: &BTreeMap<String, Vec<u8>>, namespace: &[u8; 32]) -> Result<Vec<u8>> {
    encode_measured(entries, namespace).map(|(bytes, _)| bytes)
}
#[cfg(test)]
fn decode(bytes: &[u8], namespace: &[u8; 32]) -> Result<HashMap<String, Vec<u8>>> {
    decode_measured(bytes, namespace).map(|(entries, _)| entries)
}
fn read_bounded(path: &Path) -> Result<Vec<u8>> {
    let metadata = std::fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    if !metadata.is_file() || metadata.len() > MAX_FILE { return Err("cache input is not a bounded regular file".into()); }
    let mut bytes = Vec::with_capacity(metadata.len() as usize);
    std::fs::File::open(path).map_err(|e| e.to_string())?.take(MAX_FILE + 1)
        .read_to_end(&mut bytes).map_err(|e| e.to_string())?;
    if bytes.len() as u64 > MAX_FILE { return Err("cache input grew beyond its bound".into()); }
    Ok(bytes)
}
fn replace_owned(path: &Path, bytes: &[u8]) -> Result<()> {
    // The inherited cache may be hard-linked to a finalized compiler session.
    // Always create a new inode; never truncate or write through that link.
    let temp = path.with_extension(format!("pending-{}", std::process::id()));
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(&temp)
        .map_err(|e| format!("create cache staging file: {e}"))?;
    file.write_all(bytes).map_err(|e| format!("write cache staging file: {e}"))?;
    drop(file);
    std::fs::rename(&temp, path).map_err(|e| format!("replace cache staging link: {e}"))
}

pub(crate) struct Cache {
    mode: Mode,
    path: PathBuf,
    pub namespace: [u8; 32],
    previous: HashMap<String, Vec<u8>>,
    next: BTreeMap<String, Vec<u8>>,
    load_seconds: f64,
    namespace_seconds: f64,
    file_read_seconds: f64,
    file_decoding_seconds: f64,
    file_decode_hash_seconds: f64,
    load_note: String,
    loaded_entries: usize,
    pub previous_hits: usize,
    pub red_functions: usize,
    pub green_missing: usize,
    pub current_encoding_seconds: f64,
    pub previous_decoding_seconds: f64,
    pub previous_binding_seconds: f64,
    pub green_check_seconds: f64,
    pub lowered_functions: usize,
    pub skipped_functions: usize,
    pub declined_functions: usize,
}
impl Cache {
    pub fn open(tcx: TyCtxt<'_>, trap: bool, callbacks: bool, mode: Mode) -> Result<Self> {
        let session = tcx.incr_comp_session.ok_or("function cache requires an incremental session")?;
        if !tcx.dep_graph.is_fully_enabled() { return Err("function cache requires dependency tracking".into()); }
        let path = rustc_incremental::in_incr_comp_dir_sess(session, "rust-interp-functions-v1.bin");
        let started = Instant::now();
        let executable = std::env::current_exe().map_err(|e| e.to_string())?;
        let exporter = Sha256::digest(read_bounded(&executable)?);
        let policy = format!("rust-interp-function-cache-v1\0{:?}\0{}\0{trap}\0{callbacks}",
            tcx.sess.opts.dep_tracking_hash(false), tcx.sess.opts.target_triple);
        let mut hash = Sha256::new();
        hash.update(exporter); hash.update(policy.as_bytes());
        let namespace: [u8; 32] = hash.finalize().into();
        let namespace_seconds = started.elapsed().as_secs_f64();
        let read_started = Instant::now();
        let input = read_bounded(&path);
        let file_read_seconds = read_started.elapsed().as_secs_f64();
        let decode_started = Instant::now();
        let (previous, file_decode_hash_seconds, load_note) = match input.and_then(|bytes| decode_measured(&bytes, &namespace)) {
            Ok((entries, hash_seconds)) => (entries, hash_seconds, "loaded".into()),
            Err(reason) => (HashMap::new(), 0.0, reason),
        };
        let file_decoding_seconds = decode_started.elapsed().as_secs_f64();
        let loaded_entries = previous.len();
        Ok(Self { mode, path, namespace, previous, next: BTreeMap::new(), loaded_entries, load_note,
            namespace_seconds, file_read_seconds, file_decoding_seconds, file_decode_hash_seconds,
            load_seconds: started.elapsed().as_secs_f64(), previous_hits: 0, red_functions: 0,
            green_missing: 0, current_encoding_seconds: 0.0, previous_decoding_seconds: 0.0,
            previous_binding_seconds: 0.0, green_check_seconds: 0.0, lowered_functions: 0,
            skipped_functions: 0, declined_functions: 0 })
    }
    pub fn take_previous(&mut self, node: &str, green: bool) -> Option<Vec<u8>> {
        let payload = self.previous.remove(node);
        if green {
            if payload.is_some() { self.previous_hits += 1; } else { self.green_missing += 1; }
            payload
        } else { self.red_functions += 1; None }
    }
    pub fn retain(&mut self, node: String, payload: Vec<u8>) -> Result<()> {
        if self.next.insert(node, payload).is_some() { return Err("repeated current cache node".into()); }
        Ok(())
    }
    pub fn stage(self) -> Result<()> {
        let start = Instant::now();
        let (bytes, file_encode_hash_seconds) = encode_measured(&self.next, &self.namespace)?;
        let encoding_seconds = start.elapsed().as_secs_f64();
        let start = Instant::now();
        replace_owned(&self.path, &bytes)?;
        let write_seconds = start.elapsed().as_secs_f64();
        eprintln!("rust-interp-function-cache: {}", serde_json::json!({"schema_version":1,
            "mode":if self.mode == Mode::Reuse { "reuse" } else { "verify" },
            "namespace":self.namespace.iter().map(|b| format!("{b:02x}")).collect::<String>(),
            "loaded_entries":self.loaded_entries,"load_note":self.load_note,"load_seconds":self.load_seconds,
            "namespace_seconds":self.namespace_seconds,"file_read_seconds":self.file_read_seconds,
            "file_decoding_seconds":self.file_decoding_seconds,
            "file_decode_hash_seconds":self.file_decode_hash_seconds,"file_encode_hash_seconds":file_encode_hash_seconds,
            "timing_scope":"load includes namespace/read/decode; file hash intervals are nested in file decode/encode",
            "previous_payload_uses":self.previous_hits,"red_functions":self.red_functions,"green_missing":self.green_missing,
            "staged_entries":self.next.len(),"staged_bytes":bytes.len(),"file_encoding_seconds":encoding_seconds,
            "file_write_seconds":write_seconds,"current_template_encoding_seconds":self.current_encoding_seconds,
            "previous_template_decoding_seconds":self.previous_decoding_seconds,
            "previous_binding_seconds":self.previous_binding_seconds,"green_check_seconds":self.green_check_seconds,
            "lowered_functions":self.lowered_functions,"skipped_functions":self.skipped_functions,
            "declined_functions":self.declined_functions,
            "all_original_lowering_executed":self.skipped_functions == 0,"staged_in_incremental_session":true,
            "publication":"compiler finalization is still required"}));
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn automatic_reuse_requires_both_session_and_dependency_tracking() {
        for session in [false, true] {
            for tracking in [false, true] {
                assert_eq!(effective_mode(Mode::Auto, session, tracking),
                    if session && tracking { Mode::Reuse } else { Mode::Off });
                for explicit in [Mode::Off, Mode::Reuse, Mode::Verify] {
                    assert_eq!(effective_mode(explicit, session, tracking), explicit);
                }
            }
        }
    }
    #[test]
    fn bulk_payloads_preserve_the_legacy_fixed_width_wire_bytes() {
        let entries = BTreeMap::from([("ab-cd".into(), (0..131_072).map(|n| n as u8).collect())]);
        let legacy = bincode::DefaultOptions::new().with_fixint_encoding()
            .serialize(&entries.iter().collect::<Vec<_>>()).unwrap();
        let bytes = encode(&entries, &[7; 32]).unwrap();
        assert_eq!(&bytes[HEADER..], legacy);
        assert_eq!(decode(&bytes, &[7; 32]).unwrap(), entries.into_iter().collect());
    }
    #[test]
    fn cache_bytes_bind_namespace_and_reject_corruption_truncation_and_trailing_input() {
        let values = BTreeMap::from([("1-2".into(), vec![4, 5, 6]), ("aa-bb".into(), vec![9])]);
        let bytes = encode(&values, &[7; 32]).unwrap();
        assert_eq!(decode(&bytes, &[7; 32]).unwrap(), values.clone().into_iter().collect());
        assert!(decode(&bytes, &[8; 32]).is_err());
        let mut corrupt = bytes.clone(); *corrupt.last_mut().unwrap() ^= 1;
        assert!(decode(&corrupt, &[7; 32]).is_err());
        assert!(decode(&bytes[..bytes.len()-1], &[7; 32]).is_err());
        let mut trailing = bytes; trailing.push(0);
        assert!(decode(&trailing, &[7; 32]).is_err());
        assert!(encode(&BTreeMap::from([("not-a-node".into(), vec![])]), &[7; 32]).is_err());
    }
    #[test]
    fn staged_replacement_preserves_the_prior_session_hard_link() {
        static NEXT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
        let serial = NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let dir = std::env::temp_dir().join(format!("rust-interp-function-cache-{}-{serial}", std::process::id()));
        std::fs::create_dir(&dir).unwrap();
        let prior = dir.join("prior"); let current = dir.join("current");
        std::fs::write(&prior, b"old finalized payload").unwrap();
        std::fs::hard_link(&prior, &current).unwrap();
        replace_owned(&current, b"new working payload").unwrap();
        assert_eq!(std::fs::read(&prior).unwrap(), b"old finalized payload");
        assert_eq!(std::fs::read(&current).unwrap(), b"new working payload");
        std::fs::remove_file(prior).unwrap(); std::fs::remove_file(current).unwrap();
        std::fs::remove_dir(dir).unwrap();
    }
}
