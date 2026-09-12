//! Versioned scalar call metadata. Execution support is a separate milestone.
use crate::{PARTIAL_VALIDATION, Program, Reg, VERSION};
use bincode::Options;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

pub const SCALAR_VERSION: u32 = 6;
pub const MAX_ARTIFACT_BYTES: u64 = 64 * 1024 * 1024;
const MAX_FUNCTIONS: usize = 10_000;
const MAX_ARGUMENT_FIELDS: usize = 65_536;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct FunctionAbi {
    /// None uses the original argument frame slot; Some receives a scalar.
    pub arguments: Vec<Option<Reg>>,
    /// None returns the original frame slot; Some returns this scalar register.
    pub result: Option<Reg>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Artifact {
    pub program: Program,
    pub scalar_abi: Vec<FunctionAbi>,
}

fn width(size: usize) -> bool {
    matches!(size, 1 | 2 | 4 | 8 | 16)
}

pub(crate) fn truncate(value: u128, size: usize) -> u128 {
    debug_assert!(width(size));
    if size == 16 {
        value
    } else {
        value & ((1u128 << (size * 8)) - 1)
    }
}

impl Artifact {
    pub fn legacy(program: Program) -> Result<Self, String> {
        let out = Self {
            program,
            scalar_abi: vec![],
        };
        out.validate()?;
        Ok(out)
    }

    pub fn scalar(mut program: Program, scalar_abi: Vec<FunctionAbi>) -> Result<Self, String> {
        if !matches!(program.version, VERSION | SCALAR_VERSION) {
            return Err("scalar ABI requires fully checked bytecode".into());
        }
        program.version = SCALAR_VERSION;
        let out = Self {
            program,
            scalar_abi,
        };
        out.validate()?;
        Ok(out)
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.program.version & !PARTIAL_VALIDATION == VERSION {
            if !self.scalar_abi.is_empty() {
                return Err("legacy bytecode has scalar ABI metadata".into());
            }
            return crate::validate(&self.program);
        }
        if self.program.version != SCALAR_VERSION {
            return Err("unsupported scalar artifact version".into());
        }
        crate::validate_structure(&self.program)?;
        if self.scalar_abi.len() != self.program.functions.len()
            || self.scalar_abi.len() > MAX_FUNCTIONS
        {
            return Err("scalar ABI function table mismatch or bound exceeded".into());
        }
        let mut fields = 0usize;
        for (function, abi) in self.program.functions.iter().zip(&self.scalar_abi) {
            if abi.arguments.len() != function.args.len() {
                return Err("scalar ABI argument count mismatch".into());
            }
            fields = fields
                .checked_add(abi.arguments.len())
                .filter(|&n| n <= MAX_ARGUMENT_FIELDS)
                .ok_or("scalar ABI argument table bound exceeded")?;
            let mut used = BTreeSet::new();
            for (slot, register) in function.args.iter().zip(&abi.arguments) {
                if let Some(register) = register {
                    if *register as usize >= function.registers
                        || !width(slot.size)
                        || !used.insert(*register)
                    {
                        return Err("invalid or duplicated scalar argument register".into());
                    }
                }
            }
            if let Some(register) = abi.result {
                if register as usize >= function.registers || !width(function.result.size) {
                    return Err("invalid scalar result register".into());
                }
            }
        }
        Ok(())
    }

    pub fn encode(&self) -> Result<Vec<u8>, String> {
        self.validate()?;
        let bytes = if self.program.version == SCALAR_VERSION {
            bincode::serialize(self)
        } else {
            bincode::serialize(&self.program)
        }
        .map_err(|e| e.to_string())?;
        if bytes.len() as u64 > MAX_ARTIFACT_BYTES {
            return Err("artifact byte bound exceeded".into());
        }
        Ok(bytes)
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, String> {
        if bytes.len() < 4 || bytes.len() as u64 > MAX_ARTIFACT_BYTES {
            return Err("invalid artifact length".into());
        }
        let version = u32::from_le_bytes(bytes[..4].try_into().unwrap());
        let options = bincode::DefaultOptions::new()
            .with_fixint_encoding()
            .with_limit(MAX_ARTIFACT_BYTES)
            .reject_trailing_bytes();
        let out = if version & !PARTIAL_VALIDATION == VERSION {
            Self {
                program: options.deserialize(bytes).map_err(|e| e.to_string())?,
                scalar_abi: vec![],
            }
        } else if version == SCALAR_VERSION {
            options.deserialize(bytes).map_err(|e| e.to_string())?
        } else {
            return Err("unsupported artifact version".into());
        };
        out.validate()?;
        Ok(out)
    }
}

#[cfg(test)]
#[path = "scalar_abi_artifact_tests.rs"]
mod tests;

#[path = "scalar_abi_runtime.rs"]
mod runtime;
