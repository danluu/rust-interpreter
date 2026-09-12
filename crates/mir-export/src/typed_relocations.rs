//! Typed pointer holes for a diagnostic code-template census, never executable rewrites.
use rust_interp_bytecode::{Function, Op, Reg};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Kind { Allocation, Static, Function, VTable, ThreadLocal, CallerLocation, Errno }

pub(crate) struct Binding {
    pub register: Reg,
    pub original: u128,
    pub addend: u64,
    pub kind: Kind,
    // Diagnostic identity in this compiler session, not a cross-session key.
    pub target: String,
}

pub(crate) struct Template {
    pub sha256: String,
    pub bindings: Vec<Value>,
}

pub(crate) fn inspect(function: &Function, bindings: Vec<Binding>) -> Result<Template, String> {
    if bincode::serialized_size(function).map_err(|e| e.to_string())? > 64 * 1024 * 1024 {
        return Err("typed relocation function exceeds diagnostic byte bound".into());
    }
    if bindings.len() > 100_000 {
        return Err("typed relocation count exceeds diagnostic bound".into());
    }
    let mut by_register = BTreeMap::new();
    for binding in bindings {
        if by_register.insert(binding.register, binding).is_some() {
            return Err("duplicate typed relocation register".into());
        }
    }
    let original = bincode::serialize(function).map_err(|e| e.to_string())?;
    let mut template = function.clone();
    let mut sites = vec![];
    let mut observed = BTreeSet::new();
    for (pc, op) in template.code.iter_mut().enumerate() {
        if let Op::Imm { dst, value } = op {
            if let Some(binding) = by_register.remove(dst) {
                observed.insert(*dst);
                if *value != binding.original {
                    return Err("typed relocation immediate changed during local passes".into());
                }
                *value = (*value & !u128::from(u64::MAX)) | u128::from(binding.addend);
                sites.push((pc, binding));
            } else if observed.contains(dst) {
                return Err("typed relocation register has ambiguous immediate definitions".into());
            }
        }
    }
    if !by_register.is_empty() {
        return Err("typed relocation definition disappeared during local passes".into());
    }
    let mut digest = Sha256::new();
    digest.update(b"rust-interp-typed-template-v1\0");
    digest.update(bincode::serialize(&template).map_err(|e| e.to_string())?);
    // Target identity is a binding input. Site, category and addend remain
    // part of the template; equal raw words in different categories differ.
    for (pc, binding) in &sites {
        digest.update((*pc as u64).to_le_bytes());
        digest.update(format!("{:?}\0", binding.kind).as_bytes());
        digest.update(binding.addend.to_le_bytes());
    }
    let sha256 = format!("{:x}", digest.finalize());
    let mut report = Vec::with_capacity(sites.len());
    for (pc, binding) in sites {
        let Op::Imm { value, .. } = &mut template.code[pc] else { unreachable!() };
        *value = binding.original;
        report.push(json!({"pc": pc, "register": binding.register, "kind": format!("{:?}", binding.kind),
            "original_hex": format!("{:032x}", binding.original), "addend": binding.addend,
            "target": binding.target, "pointer_bits": 64}));
    }
    if bincode::serialize(&template).map_err(|e| e.to_string())? != original {
        return Err("typed relocation bindings did not reconstruct the original function".into());
    }
    Ok(Template { sha256, bindings: report })
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_interp_bytecode::Slot;

    fn function(pointer: u128, ordinary: u128) -> Function {
        Function { name: "f".into(), frame_size: 0, frame_align: 16, registers: 2,
            args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![
                Op::Imm { dst: 0, value: pointer }, Op::Imm { dst: 1, value: ordinary }, Op::Return] }
    }
    fn binding(value: u128, addend: u64, kind: Kind) -> Vec<Binding> {
        vec![Binding { register: 0, original: value, addend, kind, target: "session-only:7".into() }]
    }

    #[test]
    fn only_typed_pointer_words_change_and_originals_reconstruct() {
        let a = function((13 << 64) | 128, 128);
        let b = function((13 << 64) | 256, 128);
        let bytes = bincode::serialize(&a).unwrap();
        let template = inspect(&a, binding((13 << 64) | 128, 0, Kind::Allocation)).unwrap();
        assert_eq!(template.sha256, inspect(&b, binding((13 << 64) | 256, 0, Kind::Allocation)).unwrap().sha256);
        assert_ne!(template.sha256, inspect(&function((14 << 64) | 128, 128), binding((14 << 64) | 128, 0, Kind::Allocation)).unwrap().sha256);
        assert_ne!(template.sha256, inspect(&function((13 << 64) | 128, 256), binding((13 << 64) | 128, 0, Kind::Allocation)).unwrap().sha256);
        assert_eq!(bincode::serialize(&a).unwrap(), bytes);
        assert_eq!(template.bindings.len(), 1);
    }

    #[test]
    fn retains_wrapped_addends_categories_and_unannotated_numeric_bits() {
        let f = function(31, 0);
        let hash = inspect(&f, binding(31, u64::MAX, Kind::Static)).unwrap().sha256;
        assert_ne!(hash, inspect(&f, binding(31, 0, Kind::Static)).unwrap().sha256);
        assert_ne!(hash, inspect(&f, binding(31, u64::MAX, Kind::Function)).unwrap().sha256);
        // TypeId provenance is never supplied as a binding by the exporter.
        assert_ne!(inspect(&function(31, 0), vec![]).unwrap().sha256,
                   inspect(&function(32, 0), vec![]).unwrap().sha256);
    }

    #[test]
    fn rejects_missing_duplicate_and_changed_definitions() {
        let mut f = function(128, 0);
        let mut bindings = binding(128, 0, Kind::Allocation);
        bindings.extend(binding(128, 0, Kind::Allocation));
        assert!(inspect(&f, bindings).is_err());
        assert!(inspect(&f, binding(127, 0, Kind::Allocation)).is_err());
        f.code[0] = Op::Return;
        assert!(inspect(&f, binding(128, 0, Kind::Allocation)).is_err());
        f.code = vec![Op::Imm { dst: 0, value: 128 }, Op::Imm { dst: 0, value: 128 }];
        assert!(inspect(&f, binding(128, 0, Kind::Allocation)).is_err());
    }
}
