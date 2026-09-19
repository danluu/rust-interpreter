//! Bounded opaque HIR records owned by one incremental compilation session.
//!
//! This module has no HIR or lowering-state access. Record keys, checksums and
//! all semantic proofs are checked by the caller on every lookup. Only explicit
//! successful-session finalization may publish queued bytes; Drop performs no IO.
use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicU64, Ordering};


const MAGIC: &[u8; 8] = b"RHIRPK01";
pub const MAX_RECORD: usize = 4 * 1024 * 1024;
const MAX_PACK: usize = 256 * 1024 * 1024;
const MAX_ENTRIES: usize = 65_536;
const HEADER: usize = 12;
const ENTRY_HEADER: usize = 36; // 32 hexadecimal owner bytes, u32 record length.
static NEXT: AtomicU64 = AtomicU64::new(0);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Policy { Capture, Reuse }
impl Policy {
    fn index(self) -> usize { match self { Self::Capture => 0, Self::Reuse => 1 } }
    pub fn filename(self) -> &'static str {
        match self {
            Self::Capture => "hir-body-capture-v2-cold-materialization-1.pack",
            Self::Reuse => "hir-body-reuse-v2-ready-hit-1.pack",
        }
    }
}

struct Pack {
    records: BTreeMap<[u8; 32], Arc<[u8]>>,
    bytes: usize,
    dirty: bool,
}
impl Default for Pack {
    fn default() -> Self { Self { records: BTreeMap::new(), bytes: HEADER, dirty: false } }
}
struct State { packs: [Option<Pack>; 2], finalized: bool }
pub struct HirBodyCache { directory: PathBuf, state: Mutex<State> }
impl HirBodyCache {
    pub fn new(directory: PathBuf) -> Self {
        Self { directory, state: Mutex::new(State { packs: [None, None], finalized: false }) }
    }
}

fn owner_id(owner: &str) -> Option<[u8; 32]> {
    let key: [u8; 32] = owner.as_bytes().try_into().ok()?;
    key.iter().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(b)).then_some(key)
}
fn invalid() -> io::Error { io::Error::new(io::ErrorKind::InvalidData, "invalid HIR cache pack") }

// Sequential framing has no unchecked offsets or permissive duplicate keys.
// All arithmetic and budgets precede the affected allocation/read.
fn decode(mut bytes: &[u8]) -> Option<Pack> {
    if bytes.len() < HEADER || bytes.len() > MAX_PACK || &bytes[..8] != MAGIC { return None; }
    let count = u32::from_le_bytes(bytes[8..12].try_into().ok()?) as usize;
    if count > MAX_ENTRIES { return None; }
    let total = bytes.len();
    bytes = &bytes[HEADER..];
    let mut records = BTreeMap::new();
    let mut previous = None;
    for _ in 0..count {
        if bytes.len() < ENTRY_HEADER { return None; }
        let owner = owner_id(std::str::from_utf8(&bytes[..32]).ok()?)?;
        if previous.is_some_and(|value| value >= owner) { return None; }
        let length = u32::from_le_bytes(bytes[32..36].try_into().ok()?) as usize;
        if length == 0 || length > MAX_RECORD { return None; }
        let end = ENTRY_HEADER.checked_add(length)?;
        if end > bytes.len() { return None; }
        records.insert(owner, Arc::from(&bytes[ENTRY_HEADER..end]));
        bytes = &bytes[end..];
        previous = Some(owner);
    }
    if !bytes.is_empty() { return None; }
    Some(Pack { records, bytes: total, dirty: false })
}

fn read_pack(path: &Path) -> Option<Pack> {
    // Each descriptor supplies its own bounded metadata/content. A link at the
    // cache pathname is rejected both before and after opening it. Semantic
    // record checks are mandatory even if another actor mutates cache bytes.
    if !fs::symlink_metadata(path).ok()?.is_file() { return None; }
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NOFOLLOW);
    }
    let file = options.open(path).ok()?;
    let metadata = file.metadata().ok()?;
    if !metadata.is_file() || metadata.len() > MAX_PACK as u64 { return None; }
    if !fs::symlink_metadata(path).ok()?.is_file() { return None; }
    let mut bytes = Vec::new();
    file.take(MAX_PACK as u64 + 1).read_to_end(&mut bytes).ok()?;
    decode(&bytes)
}

impl HirBodyCache {
    pub fn read(&self, policy: Policy, owner: &str) -> Option<Arc<[u8]>> {
        let key = owner_id(owner)?;
        let mut state = self.state.lock().ok()?;
        if state.finalized { return None; }
        let pack = state.packs[policy.index()]
            .get_or_insert_with(|| read_pack(&self.directory.join(policy.filename())).unwrap_or_default());
        pack.records.get(&key).cloned()
    }

    /// Accept already validated serialized bytes into this session only.
    /// True does not claim disk publication. No current-context proof is stored.
    pub fn queue(&self, policy: Policy, owner: &str, bytes: Vec<u8>) -> bool {
        let Some(key) = owner_id(owner) else { return false; };
        if bytes.is_empty() || bytes.len() > MAX_RECORD { return false; }
        let Ok(mut state) = self.state.lock() else { return false; };
        if state.finalized { return false; }
        let pack = state.packs[policy.index()]
            .get_or_insert_with(|| read_pack(&self.directory.join(policy.filename())).unwrap_or_default());
        if pack.records.get(&key).is_some_and(|old| old.as_ref() == bytes.as_slice()) { return true; }
        let old_size = pack.records.get(&key).map_or(0, |old| ENTRY_HEADER + old.len());
        let Some(total) = pack.bytes.checked_sub(old_size)
            .and_then(|n| n.checked_add(ENTRY_HEADER)).and_then(|n| n.checked_add(bytes.len()))
            else { return false; };
        if total > MAX_PACK || (!pack.records.contains_key(&key) && pack.records.len() >= MAX_ENTRIES) {
            return false;
        }
        pack.records.insert(key, Arc::from(bytes));
        pack.bytes = total;
        pack.dirty = true;
        true
    }

    /// Called exactly at successful incremental-session finalization, before
    /// the directory rename. Never called from Drop, an error or callback Stop.
    /// A failed pack replacement keeps the inherited pack and ordinary semantics.
    pub fn finalize(&self) -> Vec<(Policy, bool)> {
        let Ok(mut state) = self.state.lock() else {
            return vec![(Policy::Capture, false), (Policy::Reuse, false)];
        };
        if state.finalized { return Vec::new(); }
        state.finalized = true;
        let mut outcomes = Vec::new();
        for policy in [Policy::Capture, Policy::Reuse] {
            if let Some(pack) = &state.packs[policy.index()] {
                if pack.dirty { outcomes.push((policy, write_pack(&self.directory, policy, pack).is_ok())); }
            }
        }
        outcomes
    }
}

fn write_pack(directory: &Path, policy: Policy, pack: &Pack) -> io::Result<()> {
    if pack.records.len() > MAX_ENTRIES || pack.bytes > MAX_PACK { return Err(invalid()); }
    let path = directory.join(policy.filename());
    let temp = directory.join(format!("{}.part-{}-{}", policy.filename(),
        std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
    let mut file = OpenOptions::new().create_new(true).write(true).open(&temp)?;
    let result = (|| {
        file.write_all(MAGIC)?;
        file.write_all(&(pack.records.len() as u32).to_le_bytes())?;
        let mut total = HEADER;
        for (owner, record) in &pack.records {
            if record.is_empty() || record.len() > MAX_RECORD { return Err(invalid()); }
            total = total.checked_add(ENTRY_HEADER).and_then(|n| n.checked_add(record.len()))
                .filter(|n| *n <= MAX_PACK).ok_or_else(invalid)?;
            file.write_all(owner)?;
            file.write_all(&(record.len() as u32).to_le_bytes())?;
            file.write_all(record)?;
        }
        if total != pack.bytes { return Err(invalid()); }
        file.flush()
    })();
    drop(file);
    let result = result.and_then(|()| fs::rename(&temp, &path));
    if result.is_err() { let _ = fs::remove_file(&temp); }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    const OWNER: &str = "0123456789abcdef0123456789abcdef";
    fn directory() -> std::path::PathBuf {
        let p = std::env::temp_dir().join(format!("hir-pack-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
        fs::create_dir(&p).unwrap(); p
    }
    fn encoded(entries: &[(&str, &[u8])]) -> Vec<u8> {
        let mut b = MAGIC.to_vec(); b.extend_from_slice(&(entries.len() as u32).to_le_bytes());
        for (key, value) in entries {
            b.extend_from_slice(key.as_bytes()); b.extend_from_slice(&(value.len() as u32).to_le_bytes()); b.extend_from_slice(value);
        }
        b
    }
    #[test]
    fn framing_rejects_bad_magic_count_order_duplicates_lengths_and_trailing_bytes() {
        let good = encoded(&[(OWNER, b"record")]); assert!(decode(&good).is_some());
        for n in 0..good.len() { assert!(decode(&good[..n]).is_none()); }
        let mut bad=good.clone(); bad[0]=0; assert!(decode(&bad).is_none());
        let mut bad=good.clone(); bad[8..12].copy_from_slice(&((MAX_ENTRIES+1) as u32).to_le_bytes()); assert!(decode(&bad).is_none());
        let mut bad=good.clone(); bad[44..48].copy_from_slice(&((MAX_RECORD+1) as u32).to_le_bytes()); assert!(decode(&bad).is_none());
        let mut bad=good.clone(); bad.push(0); assert!(decode(&bad).is_none());
        assert!(decode(&encoded(&[(OWNER,b"a"),(OWNER,b"b")])).is_none());
        assert!(decode(&encoded(&[("ffffffffffffffffffffffffffffffff",b"a"),(OWNER,b"b")])).is_none());
        assert!(decode(&encoded(&[("x123456789abcdef0123456789abcdef",b"a")])).is_none());
        assert!(decode(&encoded(&[(OWNER,b"")])).is_none());
        assert!(decode(&vec![0;MAX_PACK+1]).is_none());
    }
    #[test]
    fn queue_is_private_and_hardlinked_previous_pack_is_immutable() {
        let d=directory(); let old=directory(); let policy=Policy::Reuse;
        let first=HirBodyCache::new(old.clone()); assert!(first.queue(policy,OWNER,b"old".to_vec()));
        assert!(!old.join(policy.filename()).exists()); assert_eq!(first.finalize(),vec![(policy,true)]);
        let previous=fs::read(old.join(policy.filename())).unwrap();
        fs::hard_link(old.join(policy.filename()),d.join(policy.filename())).unwrap();
        let next=HirBodyCache::new(d.clone()); assert_eq!(next.read(policy,OWNER).unwrap().as_ref(),b"old");
        assert!(next.queue(policy,OWNER,b"new".to_vec())); assert_eq!(next.read(policy,OWNER).unwrap().as_ref(),b"new");
        assert_eq!(fs::read(d.join(policy.filename())).unwrap(),previous);
        assert_eq!(next.finalize(),vec![(policy,true)]); assert_eq!(fs::read(old.join(policy.filename())).unwrap(),previous);
        assert_eq!(HirBodyCache::new(d.clone()).read(policy,OWNER).unwrap().as_ref(),b"new");
        assert!(next.read(policy,OWNER).is_none()); assert!(!next.queue(policy,OWNER,b"late".to_vec()));
        assert!(next.finalize().is_empty()); fs::remove_dir_all(d).unwrap(); fs::remove_dir_all(old).unwrap();
    }
    #[test]
    fn drop_no_publication_policy_separation_and_unchanged_hit_no_rewrite() {
        let d=directory(); let abandoned=HirBodyCache::new(d.clone()); assert!(abandoned.queue(Policy::Reuse,OWNER,b"abandoned".to_vec())); drop(abandoned);
        assert_eq!(fs::read_dir(&d).unwrap().count(),0);
        let first=HirBodyCache::new(d.clone()); assert!(first.queue(Policy::Capture,OWNER,b"capture".to_vec())); first.finalize();
        let next=HirBodyCache::new(d.clone()); assert!(next.read(Policy::Reuse,OWNER).is_none());
        assert_eq!(next.read(Policy::Capture,OWNER).unwrap().as_ref(),b"capture");
        assert!(next.queue(Policy::Capture,OWNER,b"capture".to_vec())); assert!(next.finalize().is_empty());
        fs::remove_dir_all(d).unwrap();
    }
    #[test]
    fn corrupt_inherited_pack_and_bounded_queue_are_cache_misses() {
        let d=directory(); fs::write(d.join(Policy::Reuse.filename()),b"bad").unwrap();
        let cache=HirBodyCache::new(d.clone()); assert!(cache.read(Policy::Reuse,OWNER).is_none());
        assert!(!cache.queue(Policy::Reuse,"../x",vec![1])); assert!(!cache.queue(Policy::Reuse,OWNER,vec![0;MAX_RECORD+1]));
        assert!(cache.queue(Policy::Reuse,OWNER,b"recovered".to_vec())); assert_eq!(cache.finalize(),vec![(Policy::Reuse,true)]);
        assert_eq!(HirBodyCache::new(d.clone()).read(Policy::Reuse,OWNER).unwrap().as_ref(),b"recovered"); fs::remove_dir_all(d).unwrap();
    }
    #[test]
    fn distinct_session_owners_and_parallel_updates_do_not_share_state() {
        let a=directory(); let b=directory();
        let first=Arc::new(HirBodyCache::new(a.clone()));
        let second=HirBodyCache::new(b.clone());
        std::thread::scope(|scope| {
            for index in 0..16 {
                let cache=Arc::clone(&first);
                scope.spawn(move || {
                    let owner=format!("{index:032x}");
                    assert!(cache.queue(Policy::Reuse,&owner,vec![index as u8]));
                    assert_eq!(cache.read(Policy::Reuse,&owner).unwrap().as_ref(),&[index as u8]);
                });
            }
        });
        assert!(second.read(Policy::Reuse,&format!("{:032x}",0)).is_none());
        assert_eq!(first.finalize(),vec![(Policy::Reuse,true)]);
        let fresh=HirBodyCache::new(a.clone());
        for index in 0..16 {
            assert_eq!(fresh.read(Policy::Reuse,&format!("{index:032x}")).unwrap().as_ref(),&[index as u8]);
        }
        assert_eq!(fs::read_dir(&b).unwrap().count(),0);
        fs::remove_dir_all(a).unwrap(); fs::remove_dir_all(b).unwrap();
    }
    #[test]
    fn total_size_and_entry_count_limits_refuse_only_new_bytes() {
        let d=directory(); let cache=HirBodyCache::new(d.clone());
        {
            // Exercise admission bounds without allocating a quarter GiB.
            // The fake pack is never serialized or presented to a reader.
            let mut state=cache.state.lock().unwrap();
            state.packs[Policy::Reuse.index()]=Some(Pack {bytes:MAX_PACK,..Pack::default()});
        }
        assert!(!cache.queue(Policy::Reuse,OWNER,vec![1]));
        {
            let mut state=cache.state.lock().unwrap();
            let pack=state.packs[Policy::Reuse.index()].as_mut().unwrap();
            *pack=Pack::default();
            for index in 0..MAX_ENTRIES {
                pack.records.insert(owner_id(&format!("{index:032x}")).unwrap(),Arc::from(&b"x"[..]));
                pack.bytes+=ENTRY_HEADER+1;
            }
        }
        assert!(!cache.queue(Policy::Reuse,OWNER,vec![1]));
        assert!(cache.queue(Policy::Reuse,&format!("{:032x}",0),b"replacement".to_vec()));
        drop(cache); assert_eq!(fs::read_dir(&d).unwrap().count(),0); fs::remove_dir_all(d).unwrap();
    }
    #[cfg(unix)]
    #[test]
    fn symlink_pack_is_not_read_or_written_through() {
        let d=directory(); let original=directory(); let policy=Policy::Reuse;
        let first=HirBodyCache::new(original.clone()); assert!(first.queue(policy,OWNER,b"old".to_vec())); first.finalize();
        let before=fs::read(original.join(policy.filename())).unwrap();
        std::os::unix::fs::symlink(original.join(policy.filename()),d.join(policy.filename())).unwrap();
        let next=HirBodyCache::new(d.clone()); assert!(next.read(policy,OWNER).is_none());
        assert!(next.queue(policy,OWNER,b"new".to_vec())); assert_eq!(next.finalize(),vec![(policy,true)]);
        assert_eq!(fs::read(original.join(policy.filename())).unwrap(),before);
        assert!(!fs::symlink_metadata(d.join(policy.filename())).unwrap().file_type().is_symlink());
        fs::remove_dir_all(d).unwrap(); fs::remove_dir_all(original).unwrap();
    }
    #[test]
    fn rename_failure_keeps_existing_destination_and_removes_owned_temp() {
        let d=directory(); fs::create_dir(d.join(Policy::Reuse.filename())).unwrap();
        let cache=HirBodyCache::new(d.clone()); assert!(cache.queue(Policy::Reuse,OWNER,b"queued".to_vec()));
        assert_eq!(cache.finalize(),vec![(Policy::Reuse,false)]); assert!(d.join(Policy::Reuse.filename()).is_dir());
        assert_eq!(fs::read_dir(&d).unwrap().count(),1); fs::remove_dir_all(d).unwrap();
    }
}
