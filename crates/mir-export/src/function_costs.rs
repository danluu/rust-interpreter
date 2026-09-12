//! Cost-weighted output census. Equal output is not a semantic cache key.
use rust_interp_bytecode::{Function, Program};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::time::Duration;

const MAX_FUNCTIONS: usize = 10_000;
const MAX_FUNCTION_BYTES: u64 = 64 * 1024 * 1024;
const MAX_REPORT_BYTES: usize = 16 * 1024 * 1024;

pub(crate) fn enabled() -> Result<bool, String> {
    match std::env::var_os("RUST_INTERP_FUNCTION_COSTS") {
        None => Ok(false),
        Some(value) if value == "0" => Ok(false),
        Some(value) if value == "1" => Ok(true),
        _ => Err("RUST_INTERP_FUNCTION_COSTS must be 0 or 1".into()),
    }
}

fn fingerprint(function: &Function) -> Result<String, String> {
    if bincode::serialized_size(function).map_err(|e| e.to_string())? > MAX_FUNCTION_BYTES {
        return Err("function cost fingerprint exceeds the diagnostic byte limit".into());
    }
    let bytes = bincode::serialize(function).map_err(|e| e.to_string())?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}

struct Record {
    index: usize,
    name: String,
    lowered_hash: String,
    prepare: Duration,
    lower: Duration,
    mir_locals: usize,
    mir_blocks: usize,
    lowered_ops: usize,
    template: crate::typed_relocations::Template,
}

#[derive(Default)]
pub(crate) struct Costs {
    records: Vec<Record>,
    indices: BTreeSet<usize>,
}

impl Costs {
    pub fn record(&mut self, index: usize, function: &Function, prepare: Duration,
                  lower: Duration, mir_locals: usize, mir_blocks: usize,
                  bindings: Vec<crate::typed_relocations::Binding>) -> Result<(), String> {
        if self.records.len() >= MAX_FUNCTIONS || !self.indices.insert(index) {
            return Err("function cost census exceeded its bound or repeated a function".into());
        }
        self.records.push(Record {
            index, name: function.name.clone(), lowered_hash: fingerprint(function)?,
            prepare, lower, mir_locals, mir_blocks, lowered_ops: function.code.len(),
            template: crate::typed_relocations::inspect(function, bindings)?,
        });
        Ok(())
    }

    pub fn finish(self, program: &Program, artifact: &[u8]) -> Result<String, String> {
        let mut rows: Vec<Value> = Vec::with_capacity(self.records.len());
        for record in self.records {
            let function = program.functions.get(record.index)
                .ok_or("function cost index disappeared during graph passes")?;
            if function.name != record.name {
                return Err("function cost index changed identity during graph passes".into());
            }
            rows.push(json!({"index": record.index, "name": record.name,
                "lowered_sha256": record.lowered_hash, "final_sha256": fingerprint(function)?,
                "typed_template_sha256": record.template.sha256,
                "relocations": record.template.bindings,
                "prepare_seconds": record.prepare.as_secs_f64(), "lower_seconds": record.lower.as_secs_f64(),
                "mir_locals": record.mir_locals, "mir_blocks": record.mir_blocks,
                "lowered_operations": record.lowered_ops, "final_operations": function.code.len()}));
        }
        let text = serde_json::to_string(&json!({"schema_version": 2, "complete": true,
            "typed_relocations_reconstruct_original": true,
            "artifact_sha256": format!("{:x}", Sha256::digest(artifact)),
            "program_functions": program.functions.len(), "observed_functions": rows.len(),
            "unobserved_functions": program.functions.len() - rows.len(), "functions": rows,
            "scope": "Preparation and lowering only; excludes observation hashing and subsequent graph passes. Instrumented diagnostic; indexed output hashes are not semantic reuse keys."
        })).map_err(|e| e.to_string())?;
        if text.len() > MAX_REPORT_BYTES {
            return Err("function cost census exceeds the diagnostic report limit".into());
        }
        Ok(text)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_interp_bytecode::{Op, Slot, VERSION};

    fn fixture() -> Program {
        Program { version: VERSION, target: "test".into(), entry: 0,
            functions: vec![Function { name: "same-display-name".into(), frame_size: 0,
                frame_align: 16, registers: 0, args: vec![], result: Slot { offset: 0, size: 0 },
                code: vec![Op::Return] }], data: vec![], statics: vec![], thread_locals: vec![] }
    }

    #[test]
    fn binds_exact_input_and_transformed_output_without_mutation() {
        let mut program = fixture();
        let original = bincode::serialize(&program).unwrap();
        let before = fingerprint(&program.functions[0]).unwrap();
        let mut costs = Costs::default();
        costs.record(0, &program.functions[0], Duration::from_nanos(7), Duration::from_nanos(11), 1, 1, vec![]).unwrap();
        assert_eq!(bincode::serialize(&program).unwrap(), original);
        program.functions[0].frame_size = 8;
        let artifact = bincode::serialize(&program).unwrap();
        let report: Value = serde_json::from_str(&costs.finish(&program, &artifact).unwrap()).unwrap();
        assert_eq!(report["artifact_sha256"], format!("{:x}", Sha256::digest(&artifact)));
        assert_eq!(report["functions"][0]["lowered_sha256"], before);
        assert_ne!(report["functions"][0]["lowered_sha256"], report["functions"][0]["final_sha256"]);
        assert_eq!(report["functions"][0]["prepare_seconds"], 7e-9);
        assert_eq!(report["functions"][0]["lower_seconds"], 11e-9);
        assert_eq!(bincode::serialize(&program).unwrap(), artifact);
    }

    #[test]
    fn rejects_duplicate_indices_and_changed_final_identity() {
        let mut program = fixture();
        let mut costs = Costs::default();
        costs.record(0, &program.functions[0], Duration::ZERO, Duration::ZERO, 1, 1, vec![]).unwrap();
        assert!(costs.record(0, &program.functions[0], Duration::ZERO, Duration::ZERO, 1, 1, vec![]).is_err());
        program.functions[0].name = "different".into();
        assert!(costs.finish(&program, b"").is_err());
    }
}
