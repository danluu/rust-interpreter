//! Explicit test entry identities survive optimization of their batch caller.
use crate::{Program, VERSION};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

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
            || !(2..=256).contains(&self.entries.len())
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
}
