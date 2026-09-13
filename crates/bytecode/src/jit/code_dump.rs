//! Post-execution diagnostics; no instrumentation or metadata in emitted code.
use super::*;
use serde::Serialize;
use std::{io::Write, path::Path};

#[derive(Serialize)]
struct Range<'a> {
    offset: usize,
    end: usize,
    function: usize,
    name: &'a str,
    kind: &'static str,
    pc: Option<usize>,
    pc_end: Option<usize>,
}

#[derive(Serialize)]
struct Dump<'a> {
    schema_version: u32,
    pid: u32,
    architecture: &'static str,
    byte_order: &'static str,
    arena_base: usize,
    code_bytes: usize,
    profiled: bool,
    native_call_stubs: bool,
    persistent_registers: bool,
    resumable_calls: bool,
    indirect_calls: bool,
    ranges: Vec<Range<'a>>,
    note: &'static str,
}

impl Jit<'_> {
    /// Inspect only published code after execution has returned. The borrowed
    /// arena stays alive through both writes. Directory creation is exclusive;
    /// failures preserve any partial evidence and never replace existing files.
    pub(crate) fn dump_code(&self, path: &Path, operations: bool) -> Result<(), String> {
        let (arena_base, bytes) = self.code.as_ref().map_or((0, &[][..]), |c| c.published());
        if bytes.len() != self.bytes { return Err("native code dump length mismatch".into()); }
        let mut ranges = vec![];
        for (function, blocks) in self.blocks.iter().enumerate() {
            for (pc, block) in blocks.iter().enumerate() {
                let Some(block) = block else { continue; };
                ranges.push(Range { offset: block.offset, end: 0, function,
                    name: &self.program.functions[function].name,
                    kind: if self.resumable.is_some() {
                        match self.program.functions[function].code[pc] {
                            Op::Call { .. } => "resumable_call", Op::CallIndirect { .. } => "resumable_indirect_call", Op::Return => "resumable_return", _ => "resumable_region",
                        }
                    } else if matches!(self.program.functions[function].code[pc], Op::Call { .. }) { "call_stub" } else { "ordinary_region" },
                    pc: Some(pc), pc_end: Some(block.end) });
            }
        }
        if let Some(trees) = &self.trees {
            for (function, entry) in trees.entries.iter().enumerate() {
                let Some(entry) = entry else { continue; };
                ranges.push(Range { offset: entry.wrapper, end: 0, function,
                    name: &self.program.functions[function].name, kind: "native_tree",
                    pc: None, pc_end: None });
            }
        }
        ranges.sort_by_key(|r| r.offset);
        if ranges.first().is_some_and(|r| r.offset != 0) || (ranges.is_empty() != bytes.is_empty()) {
            return Err("native code dump has an unclassified prefix".into());
        }
        let mut end = bytes.len();
        for range in ranges.iter_mut().rev() {
            if range.offset >= end || range.offset % 4 != 0 || end % 4 != 0 {
                return Err("native code dump has invalid or overlapping entries".into());
            }
            range.end = end;
            end = range.offset;
        }
        let dump = Dump { schema_version: 1, pid: std::process::id(),
            architecture: "aarch64", byte_order: "little", arena_base, code_bytes: bytes.len(),
            profiled: self.profiled, native_call_stubs: self.native_call_stubs,
            persistent_registers: self.persistent_registers, resumable_calls: self.resumable.is_some(), indirect_calls: self.indirect.is_some(), ranges,
            note: "Published code from this process after successful execution. Entry ranges include wrappers, failure tails and fallbacks. Native-tree ranges cover whole functions, not individual bytecode operations. Diagnostic I/O is not benchmark evidence." };
        let operations = operations.then(|| self.operation_map()).transpose()?;
        let write = || -> Result<(), Box<dyn std::error::Error>> {
            std::fs::create_dir(path)?;
            let mut code = std::fs::OpenOptions::new().write(true).create_new(true).open(path.join("code.bin"))?;
            code.write_all(bytes)?;
            let file = std::fs::OpenOptions::new().write(true).create_new(true).open(path.join("map.json"))?;
            let mut writer = std::io::BufWriter::new(file);
            serde_json::to_writer(&mut writer, &dump)?;
            writer.flush()?;
            if let Some(operations) = operations {
                let file = std::fs::OpenOptions::new().write(true).create_new(true).open(path.join("operations.json"))?;
                operations.write(std::io::BufWriter::new(file))?;
            }
            Ok(())
        };
        write().map_err(|e| format!("write native code dump: {e}"))
    }
}
