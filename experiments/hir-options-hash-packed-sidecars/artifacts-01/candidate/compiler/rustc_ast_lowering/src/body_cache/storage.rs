//! Versioned, bounded records in an incremental-session-owned pack.
//! Raw byte storage confers no HIR authority. Every read repeats the original
//! record key/checksum check and every later current-state semantic preflight.
use std::hash::Hash;
use rustc_data_structures::{fingerprint::Fingerprint, stable_hash::StableHasher};
use rustc_session::{IncrCompSession, hir_body_cache::Policy};
use serde::{Deserialize, Serialize};
use super::{FORMAT, journal::Journal, wire::BodyTree};

pub(super) const MAX_RECORD: usize = rustc_session::hir_body_cache::MAX_RECORD;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Payload { pub journal: Journal, pub tree: BodyTree }

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Record { format: String, key: Vec<u8>, payload: Payload, checksum: String }

fn checksum(key: &[u8], payload: &Payload) -> Option<String> {
    let bytes = serde_json::to_vec(payload).ok()?;
    if bytes.len() > MAX_RECORD { return None; }
    let mut state = StableHasher::new();
    key.hash(&mut state); bytes.hash(&mut state);
    let fingerprint: Fingerprint = state.finish();
    Some(super::hex(fingerprint))
}

fn decode(bytes: &[u8], key: &[u8]) -> Option<Payload> {
    if bytes.len() > MAX_RECORD { return None; }
    let record: Record = serde_json::from_slice(bytes).ok()?;
    if record.format != FORMAT || record.key != key || record.checksum != checksum(key, &record.payload)? {
        return None;
    }
    Some(record.payload)
}

fn encode(key: &[u8], payload: &Payload) -> Option<Vec<u8>> {
    let checksum = checksum(key, payload)?;
    let record = Record { format: FORMAT.to_owned(), key: key.to_vec(), payload: payload.clone(), checksum };
    let bytes = serde_json::to_vec(&record).ok()?;
    (bytes.len() <= MAX_RECORD).then_some(bytes)
}

pub(super) fn read_record(session: &IncrCompSession, policy: Policy, owner: &str, key: &[u8]) -> Option<Payload> {
    let bytes = session.hir_body_cache.read(policy, owner)?;
    decode(&bytes, key)
}

pub(super) fn queue_record(session: &IncrCompSession, policy: Policy, owner: &str,
    key: &[u8], payload: &Payload) -> bool {
    let Some(bytes) = encode(key, payload) else { return false; };
    // This is acceptance into a pending session, not successful disk publication.
    // Incremental finalization reports the separate pack-publication outcome.
    session.hir_body_cache.queue(policy, owner, bytes)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::Path;
    use std::sync::atomic::{AtomicU64, Ordering};
    use rustc_session::hir_body_cache::HirBodyCache;
    static NEXT: AtomicU64 = AtomicU64::new(0);
    const OWNER: &str = "0123456789abcdef0123456789abcdef";
    fn directory() -> std::path::PathBuf {
        let p=std::env::temp_dir().join(format!("hir-packed-record-{}-{}",std::process::id(),NEXT.fetch_add(1,Ordering::Relaxed)));
        fs::create_dir(&p).unwrap(); p
    }
    fn read(directory: &Path, key: &[u8]) -> Option<Payload> {
        let raw=HirBodyCache::new(directory.to_owned()).read(Policy::Reuse,OWNER)?;
        decode(&raw,key)
    }
    fn write_raw(directory: &Path, raw: Vec<u8>) {
        let cache=HirBodyCache::new(directory.to_owned());
        assert!(cache.queue(Policy::Reuse,OWNER,raw));
        assert_eq!(cache.finalize(),vec![(Policy::Reuse,true)]);
    }
    fn write(directory: &Path, key: &[u8], payload: &Payload) {
        write_raw(directory,encode(key,payload).unwrap());
    }
    #[test]
    fn corrupt_truncated_wrong_key_and_hardlinked_old_inode() {
        let current=directory(); let old=directory(); let name=Policy::Reuse.filename();
        let payload=Payload { journal:super::super::validate::tests::checked().journal().clone(),tree:super::super::validate::tests::tree() };
        write(&old,b"key",&payload); let bytes=fs::read(old.join(name)).unwrap();
        fs::hard_link(old.join(name),current.join(name)).unwrap();
        write(&current,b"new-key",&payload);
        assert_eq!(fs::read(old.join(name)).unwrap(),bytes);
        assert!(read(&current,b"key").is_none()); assert!(read(&old,b"key").is_some());
        let record_bytes=encode(b"key",&payload).unwrap();
        for bad in [b"{".to_vec(),b"[]".to_vec(),record_bytes[..record_bytes.len()/2].to_vec()] {
            write_raw(&current,bad); assert!(read(&current,b"key").is_none());
        }
        // The raw pack refuses oversized records and the codec independently
        // rejects them: neither framing nor deserialization removes the bound.
        let oversized=vec![0;MAX_RECORD+1]; assert!(decode(&oversized,b"key").is_none());
        assert!(!HirBodyCache::new(current.clone()).queue(Policy::Reuse,OWNER,oversized));
        let mut record:Record=serde_json::from_slice(&record_bytes).unwrap();
        record.payload.journal.end_delta=2;
        write_raw(&current,serde_json::to_vec(&record).unwrap());
        assert!(read(&current,b"key").is_none());
        fs::remove_dir_all(current).unwrap(); fs::remove_dir_all(old).unwrap();
    }
    #[test]
    fn valid_checksum_does_not_bypass_tree_preflight() {
        use super::super::{validate,wire};
        let directory=directory();
        let checked=validate::tests::checked(); let current=validate::tests::current(&checked);
        let good=Payload { journal:checked.journal().clone(),tree:validate::tests::tree() };
        write(&directory,b"key",&good);
        assert!(validate::check(read(&directory,b"key").unwrap().tree,&current).is_some());
        // Each queued record has a VALID checksum. It must pass storage and
        // still fail the complete tree/current preflight, exactly as before.
        for fault in 0..3 {
            let mut bad=good.clone();
            match fault {
                0=>bad.tree.value.node.relative=0,
                1=>bad.tree.value.node.relative=99,
                _=>bad.tree.value.node.span=wire::SourceSpan::Relative {lo:2,hi:3},
            }
            write(&directory,b"key",&bad);
            let decoded=read(&directory,b"key").unwrap();
            assert_eq!(decoded,bad); assert!(validate::check(decoded.tree,&current).is_none());
        }
        write(&directory,b"key",&good);
        assert!(validate::check(read(&directory,b"key").unwrap().tree,&current).is_some());
        fs::remove_dir_all(directory).unwrap();
    }
}
