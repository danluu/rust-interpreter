//! Explicit test entry identities survive optimization of their batch caller.
use crate::{Program, VERSION};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

/// A digest of these exact, immutable, owned bytes. This is not a claim that
/// the bytes decode to a valid Program: decoding and validation remain required.
/// There is deliberately no constructor taking a caller-supplied digest.
#[cfg(feature = "jit-artifact-digest-reuse")]
pub struct HashedArtifactBytes {
    bytes: Vec<u8>,
    sha256: String,
}

#[cfg(all(test, feature = "jit-artifact-digest-reuse"))]
mod tests {
    use super::*;
    use crate::{Function, Op, Slot};

    fn fixture() -> (Program, EntryCatalog) {
        let function = |name: &str| Function {
            name: name.into(), frame_size: 0, frame_align: 1, registers: 0,
            args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![Op::Return],
        };
        let program = Program { version: VERSION, target: "aarch64-apple-darwin".into(),
            entry: 0, functions: vec![function("root"), function("test")],
            data: vec![1], statics: vec![], thread_locals: vec![] };
        let bytes = bincode::serialize(&program).unwrap();
        let catalog = EntryCatalog::new(&program, format!("{:x}", Sha256::digest(&bytes)),
            vec![SelectedEntry { name: "selected".into(), function: 1, body_name: "test".into() }]).unwrap();
        (program, catalog)
    }

    #[test]
    fn hashed_artifact_catalog_binds_actual_owned_bytes_across_body_edits() {
        let (program, catalog) = fixture();
        let bytes = bincode::serialize(&program).unwrap();
        let artifact = HashedArtifactBytes::new(bytes.clone());
        assert_eq!(artifact.bytes(), bytes);
        assert_eq!(artifact.sha256(), format!("{:x}", Sha256::digest(&bytes)));
        assert_eq!(catalog.validated_entries_hashed(&program, &artifact),
            catalog.validated_entries(&program, &bytes));

        let mut changed = program.clone();
        changed.data[0] = 2;
        let changed_bytes = bincode::serialize(&changed).unwrap();
        assert_eq!(changed_bytes.len(), bytes.len());
        let changed_artifact = HashedArtifactBytes::new(changed_bytes);
        assert_ne!(changed_artifact.sha256(), artifact.sha256());
        assert_eq!(catalog.validated_entries_hashed(&changed, &changed_artifact).unwrap_err(),
            "entry catalog does not match the bytecode digest");
        // Holding another artifact cannot change the original digest/bytes.
        assert_eq!(catalog.validated_entries_hashed(&program, &artifact).unwrap(), vec![("selected", 1)]);
        let mut updated = catalog.clone();
        updated.artifact_sha256 = changed_artifact.sha256().into();
        assert!(updated.validated_entries_hashed(&changed, &changed_artifact).is_ok());
        assert!(updated.validated_entries_hashed(&program, &artifact).is_err());
    }

    #[test]
    fn hashed_artifact_catalog_retains_header_and_entry_validation() {
        let (program, catalog) = fixture();
        let artifact = HashedArtifactBytes::new(bincode::serialize(&program).unwrap());
        for case in 0..15 {
            let mut invalid = catalog.clone();
            match case {
                0 => invalid.schema_version = 0,
                1 => invalid.bytecode_version = 0,
                2 => invalid.target = "other".into(),
                3 => invalid.program_entry = 1,
                4 => invalid.artifact_sha256 = "invalid".into(),
                5 => invalid.artifact_sha256 = "G".repeat(64),
                6 => invalid.artifact_sha256 = "0".repeat(64),
                7 => invalid.entries.clear(),
                8 => invalid.entries = vec![invalid.entries[0].clone(); 257],
                9 => invalid.entries.push(invalid.entries[0].clone()),
                10 => invalid.entries[0].name.clear(),
                11 => invalid.entries[0].name = "n".repeat(4097),
                12 => invalid.entries[0].function = 2,
                13 => { invalid.entries[0].function = 0; invalid.entries[0].body_name = "root".into(); },
                _ => invalid.entries[0].body_name = "different".into(),
            }
            let old = invalid.validated_entries(&program, artifact.bytes());
            assert!(old.is_err(), "accepted invalid catalog {case}");
            assert_eq!(invalid.validated_entries_hashed(&program, &artifact), old);
        }
        for case in 0..3 {
            let mut invalid = program.clone();
            match case {
                0 => invalid.version |= crate::PARTIAL_VALIDATION,
                1 => invalid.functions[1].args.push(Slot { offset: 0, size: 1 }),
                _ => invalid.functions[1].result.size = 1,
            }
            let old = catalog.validated_entries(&invalid, artifact.bytes());
            assert!(old.is_err());
            assert_eq!(catalog.validated_entries_hashed(&invalid, &artifact), old);
        }
    }
}

#[cfg(feature = "jit-artifact-digest-reuse")]
impl HashedArtifactBytes {
    pub fn new(bytes: Vec<u8>) -> Self {
        let sha256 = format!("{:x}", Sha256::digest(&bytes));
        Self { bytes, sha256 }
    }

    pub fn bytes(&self) -> &[u8] { &self.bytes }
    pub fn sha256(&self) -> &str { &self.sha256 }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SelectedEntry {
    pub name: String,
    pub function: usize,
    pub body_name: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EntryCatalog {
    schema_version: u32,
    bytecode_version: u32,
    artifact_sha256: String,
    target: String,
    program_entry: usize,
    pub entries: Vec<SelectedEntry>,
}

impl EntryCatalog {
    /// Declared digest only; consumers must still validate the actual artifact
    /// and catalog before execution with validated_entries.
    #[cfg(feature = "jit-template-session")]
    pub fn declared_artifact_sha256(&self) -> Result<&str, String> {
        if self.artifact_sha256.len()!=64 || !self.artifact_sha256.bytes()
            .all(|c|c.is_ascii_digit() || (b'a'..=b'f').contains(&c)) {
            return Err("entry catalog has an invalid artifact digest".into());
        }
        Ok(&self.artifact_sha256)
    }

    /// The exporter supplies IDs retained before optimizing the batch root.
    pub fn new(
        program: &Program,
        artifact_sha256: String,
        entries: Vec<SelectedEntry>,
    ) -> Result<Self, String> {
        let catalog = Self {
            schema_version: 1,
            bytecode_version: program.version,
            artifact_sha256,
            target: program.target.clone(),
            program_entry: program.entry,
            entries,
        };
        catalog.check_entries(program)?;
        Ok(catalog)
    }

    fn check_entries(&self, program: &Program) -> Result<(), String> {
        if self.schema_version != 1
            || self.bytecode_version != VERSION
            || program.version != VERSION
            || self.target != program.target
            || self.program_entry != program.entry
            || self.artifact_sha256.len() != 64
            || !self
                .artifact_sha256
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
            || !(1..=256).contains(&self.entries.len())
        {
            return Err("entry catalog header differs from checked bytecode".into());
        }
        let mut names = HashSet::new();
        let mut ids = HashSet::new();
        for entry in &self.entries {
            let body = program
                .functions
                .get(entry.function)
                .ok_or("entry catalog function is out of range")?;
            if entry.name.is_empty()
                || entry.name.len() > 4096
                || !names.insert(&entry.name)
                || !ids.insert(entry.function)
                || entry.function == program.entry
                || entry.body_name != body.name
                || !body.args.is_empty()
                || body.result.size != 0
            {
                return Err(
                    "entry catalog requires distinct named zero-argument/unit-result bodies".into(),
                );
            }
        }
        Ok(())
    }

    /// Validate against the exact bytes read by the VM, before any guest runs.
    pub fn validated_entries<'a>(
        &'a self,
        program: &Program,
        bytes: &[u8],
    ) -> Result<Vec<(&'a str, usize)>, String> {
        self.check_entries(program)?;
        if self.artifact_sha256 != format!("{:x}", Sha256::digest(bytes)) {
            return Err("entry catalog does not match the bytecode digest".into());
        }
        Ok(self
            .entries
            .iter()
            .map(|entry| (entry.name.as_str(), entry.function))
            .collect())
    }

    /// As with validated_entries, program must have been decoded from these
    /// bytes. Reuse only the digest computed by the immutable byte owner; retain
    /// every catalog header, entry, and body identity check.
    #[cfg(feature = "jit-artifact-digest-reuse")]
    pub fn validated_entries_hashed<'a>(
        &'a self,
        program: &Program,
        artifact: &HashedArtifactBytes,
    ) -> Result<Vec<(&'a str, usize)>, String> {
        self.check_entries(program)?;
        if self.artifact_sha256 != artifact.sha256() {
            return Err("entry catalog does not match the bytecode digest".into());
        }
        Ok(self.entries.iter().map(|entry| (entry.name.as_str(), entry.function)).collect())
    }
}
