//! Diagnostic storage for independently validated audit programs.
use rust_interp_bytecode::scalar_abi::Artifact;
use sha2::{Digest, Sha256};
use std::io::Write;
use std::path::{Path, PathBuf};

const MAX_BODY_BYTES: u64 = 64 * 1024 * 1024;
const MAX_PACK_BYTES: u64 = 1024 * 1024 * 1024;

pub struct Pack {
    directory: PathBuf,
    bytes: u64,
    files: usize,
}

impl Pack {
    pub fn new(output: &Path) -> Result<Self, String> {
        let parent = output
            .parent()
            .ok_or("audit output has no parent directory")?;
        let parent = if parent.as_os_str().is_empty() {
            Path::new(".")
        } else {
            parent
        };
        let parent = parent
            .canonicalize()
            .map_err(|e| format!("audit output parent: {e}"))?;
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|e| e.to_string())?
            .as_nanos();
        // Exclusive creation: an incomplete prior pack is never overwritten.
        let directory = parent.join(format!("audit-bodies-{}-{stamp}", std::process::id()));
        std::fs::create_dir(&directory).map_err(|e| format!("create audit body pack: {e}"))?;
        Ok(Self {
            directory,
            bytes: 0,
            files: 0,
        })
    }

    pub fn store(
        &mut self,
        index: usize,
        artifact: &Artifact,
    ) -> Result<serde_json::Value, String> {
        if index >= 4096 || self.files >= 4096 {
            return Err("audit body count exceeds 4096".into());
        }
        // The caller has validated the program. Bound serialization before
        // allocating its buffer; loading a body uses the VM's existing limits.
        let expected = if artifact.program.version == 6 {
            bincode::serialized_size(artifact)
        } else {
            bincode::serialized_size(&artifact.program)
        }
        .map_err(|e| e.to_string())?;
        if expected == 0 || expected > MAX_BODY_BYTES {
            return Err("audit body exceeds 64 MiB".into());
        }
        let total = self
            .bytes
            .checked_add(expected)
            .ok_or("audit pack size overflow")?;
        if total > MAX_PACK_BYTES {
            return Err("audit body pack exceeds 1 GiB; use a smaller selection".into());
        }
        let bytes = artifact.encode()?;
        if bytes.len() as u64 != expected {
            return Err("audit serialized size mismatch".into());
        }
        let digest = format!("{:x}", Sha256::digest(&bytes));
        let filename = format!("{index:04}.rbc");
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(self.directory.join(&filename))
            .map_err(|e| format!("create audit body: {e}"))?;
        file.write_all(&bytes)
            .map_err(|e| format!("write audit body: {e}"))?;
        // No manifest points to this pack until every successful body is
        // written and the report is atomically published beside exact metadata.
        drop(file);
        self.bytes = total;
        self.files += 1;
        Ok(serde_json::json!({"file":filename,"bytes":expected,"sha256":digest}))
    }

    pub fn describe(&self) -> serde_json::Value {
        serde_json::json!({"kind":"audit-body-pack","schema_version":1,
            "directory":self.directory,"files":self.files,"bytes":self.bytes,
            "max_body_bytes":MAX_BODY_BYTES,"max_pack_bytes":MAX_PACK_BYTES})
    }
}
