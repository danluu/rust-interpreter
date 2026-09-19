//! Immutable process input with guest-owned, read-only value storage.
use super::Memory;
use std::collections::BTreeMap;

// Charge key bytes plus a conservative fixed index allowance per binding.
const ENTRY_CHARGE: usize = 128;

pub(super) struct Snapshot {
    bytes: Vec<u8>,
    offsets: BTreeMap<Vec<u8>, usize>,
    index_bytes: usize,
}

impl Snapshot {
    pub(super) fn capture(limit: usize) -> Result<Self, String> {
        #[cfg(unix)]
        {
            use std::os::unix::ffi::OsStringExt;
            Self::from_pairs(std::env::vars_os().map(|(k, v)| (k.into_vec(), v.into_vec())), limit)
        }
        #[cfg(not(unix))]
        { let _ = limit; Err("guest environment reads require a Unix host".into()) }
    }

    pub(super) fn from_pairs(pairs: impl IntoIterator<Item = (Vec<u8>, Vec<u8>)>, limit: usize) -> Result<Self, String> {
        let mut snapshot = Self { bytes: vec![], offsets: BTreeMap::new(), index_bytes: 0 };
        for (name, value) in pairs {
            if name.contains(&0) || value.contains(&0) {
                return Err("invalid NUL in environment snapshot".into());
            }
            // getenv cannot address these names. First matching binding wins
            // for duplicate raw environment entries, as with native getenv.
            if name.is_empty() || name.contains(&b'=') || snapshot.offsets.contains_key(&name) { continue; }
            let index_bytes = snapshot.index_bytes.checked_add(name.len())
                .and_then(|n| n.checked_add(ENTRY_CHARGE)).ok_or("environment snapshot size overflow")?;
            let end = snapshot.bytes.len().checked_add(value.len())
                .and_then(|n| n.checked_add(1)).ok_or("environment snapshot size overflow")?;
            if end.checked_add(index_bytes).is_none_or(|n| n > limit) {
                return Err("environment snapshot exceeds memory limit".into());
            }
            snapshot.offsets.insert(name, snapshot.bytes.len());
            snapshot.bytes.extend_from_slice(&value);
            snapshot.bytes.push(0);
            snapshot.index_bytes = index_bytes;
        }
        Ok(snapshot)
    }

    pub(super) fn install(&self, memory: &mut Memory) -> Result<usize, String> {
        let base = memory.bytes.len();
        let end = base.checked_add(self.bytes.len()).ok_or("environment snapshot size overflow")?;
        let auxiliary = memory.auxiliary_bytes.checked_add(self.index_bytes)
            .ok_or("environment snapshot size overflow")?;
        if end >= super::heap::TAG || end.checked_add(memory.heap.bytes.len())
            .and_then(|n| n.checked_add(auxiliary)).is_none_or(|n| n > memory.limit) {
            return Err("guest environment exceeds memory limit".into());
        }
        if !self.bytes.is_empty() {
            memory.bytes.resize(end, 0);
            memory.bytes[base..end].copy_from_slice(&self.bytes);
            memory.readonly_end = end;
        }
        memory.auxiliary_bytes = auxiliary;
        memory.peak = memory.peak.max(memory.total_len());
        Ok(base)
    }

    pub(super) fn get(&self, memory: &Memory, base: usize, name: u128) -> Result<u128, String> {
        let address = usize::try_from(name).map_err(|_| "environment name pointer exceeds address width")?;
        let (heap, range) = memory.range(address, 1)?;
        let tail = if heap { &memory.heap.bytes[range.start..] } else { &memory.bytes[range.start..] };
        let length = tail.iter().position(|&b| b == 0).ok_or("unterminated guest environment name")?;
        let name = &tail[..length];
        Ok(self.offsets.get(name).map_or(0, |&offset| (base + offset) as u128))
    }
}

#[cfg(test)]
mod tests;
