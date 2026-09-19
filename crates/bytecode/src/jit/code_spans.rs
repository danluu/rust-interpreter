//! Reconstruct operation ownership only after execution, then verify live code.
use super::*;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::io::{self, Write};

const MAX_SPANS: usize = 2_000_000;
const MAX_OUTPUT_BYTES: usize = 256 * 1024 * 1024;

#[cfg(test)]
mod local_census;
#[cfg(test)]
mod protocol_census;
#[cfg(test)]
mod scalar_entry_scope;
#[cfg(test)]
mod ordinary_padding_scope;
#[cfg(test)]
mod scratch_census;
#[cfg(test)]
mod flush_census;
#[cfg(test)]
mod memory_parts;
#[cfg(test)]
mod continuation_census;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(super) enum Kind {
    Entry, RangeGuard, Budget, Profile, Operation, Flush, RegionExit, FaultTail,
    AssertionTail, BudgetFallback, SuccessorFallback, Transition, ScalarLeaf,
}

#[derive(Debug, Serialize)]
pub(super) struct Span {
    offset: usize,
    end: usize,
    region_pc: usize,
    pc: Option<usize>,
    kind: Kind,
}

pub(super) struct Collector {
    rows: Vec<Span>,
    limit: usize,
}

pub(super) fn record(sink: &mut Option<&mut Collector>, word_base: usize,
    region_pc: usize, pc: Option<usize>, kind: Kind, start: usize, end: usize,
) -> Result<(), EmitError> {
    let Some(sink) = sink else { return Ok(()); };
    if start == end && pc.is_none() { return Ok(()); }
    if sink.rows.len() >= sink.limit { return Err(EmitError::Limit(CodegenLimit::OperationMap)); }
    let byte = |word| word_base.checked_add(word).and_then(|n| n.checked_mul(4))
        .ok_or(EmitError::InvalidRelocation("operation map offset overflow"));
    sink.rows.push(Span { offset: byte(start)?, end: byte(end)?, region_pc, pc, kind });
    Ok(())
}

impl Collector {
    fn validate(&self, f: &Function, staged: &CompiledFunction<'_>) -> Result<(), String> {
        let bytes = staged.words.len() * 4;
        let entries: Vec<_> = staged.entries.iter().enumerate()
            .filter_map(|(pc, entry)| entry.map(|entry| (pc, entry))).collect();
        let mut regions = BTreeMap::new();
        for (i, &(pc, entry)) in entries.iter().enumerate() {
            let end = entries.get(i + 1).map_or(bytes, |(_, e)| e.offset);
            if pc >= entry.end || entry.end > f.code.len() || entry.offset >= end {
                return Err("operation map invalid region".into());
            }
            regions.insert(pc, (entry, end));
        }
        let mut seen = vec![false; f.code.len()];
        let mut cursor = 0;
        for row in &self.rows {
            if row.offset != cursor || row.end < row.offset || row.end > bytes
                || row.offset % 4 != 0 || row.end % 4 != 0 {
                return Err("operation map gap, overlap or invalid offset".into());
            }
            let (region, end) = regions.get(&row.region_pc).ok_or("operation map missing region")?;
            if row.offset < region.offset || row.end > *end {
                return Err("operation map span crosses its region".into());
            }
            if let Some(pc) = row.pc {
                if !matches!(row.kind, Kind::Operation | Kind::Transition)
                    || pc < row.region_pc || pc >= region.end || seen[pc] {
                    return Err("operation map invalid or repeated PC".into());
                }
                if row.kind == Kind::Transition && !matches!(f.code[pc], Op::Call { .. } | Op::Return) {
                    return Err("operation map invalid transition PC".into());
                }
                seen[pc] = true;
            } else if matches!(row.kind, Kind::Operation | Kind::Transition) || row.offset == row.end {
                return Err("operation map missing PC or empty overhead span".into());
            }
            cursor = row.end;
        }
        if cursor != bytes { return Err("operation map incomplete byte coverage".into()); }
        let mut expected = vec![false; f.code.len()];
        for (pc, entry) in entries { expected[pc..entry.end].fill(true); }
        if seen != expected { return Err("operation map incomplete PC coverage".into()); }
        Ok(())
    }
}

#[derive(Debug, Serialize)]
struct FunctionMap<'a> {
    function: usize,
    name: &'a str,
    offset: usize,
    end: usize,
    assertion_base: usize,
    assertion_count: usize,
    spans: Vec<Span>,
}

#[derive(Debug, Serialize)]
pub(super) struct Map<'a> {
    schema_version: u32,
    pid: u32,
    arena_base: usize,
    code_bytes: usize,
    code_sha256: String,
    profiled: bool,
    persistent_registers: bool,
    resumable_calls: bool,
    complete: bool,
    reconstructed_bytes_match: bool,
    spans: usize,
    functions: Vec<FunctionMap<'a>>,
    note: &'static str,
}

struct Limited<W> { writer: W, remaining: usize }
impl<W: Write> Write for Limited<W> {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if bytes.len() > self.remaining { return Err(io::Error::other("operation map output bound")); }
        let n = self.writer.write(bytes)?;
        self.remaining -= n;
        Ok(n)
    }
    fn flush(&mut self) -> io::Result<()> { self.writer.flush() }
}
impl Map<'_> {
    pub(super) fn write(&self, writer: impl Write) -> Result<(), String> {
        let mut writer = Limited { writer, remaining: MAX_OUTPUT_BYTES };
        serde_json::to_writer(&mut writer, self).map_err(|e| e.to_string())?;
        writer.flush().map_err(|e| e.to_string())
    }
}

impl Jit<'_> {
    pub(super) fn operation_map(&self) -> Result<Map<'_>, String> {
        if self.trees.is_some() || self.native_call_stubs {
            return Err("operation maps do not support native trees or stubs".into());
        }
        let (arena_base, bytes) = self.code.as_ref().map_or((0, &[][..]), |code| code.published());
        if bytes.len() != self.bytes { return Err("operation map code length mismatch".into()); }
        let mut order: Vec<_> = self.blocks.iter().enumerate().filter_map(|(id, entries)|
            entries.iter().flatten().map(|entry| entry.offset).min().map(|offset| (offset, id, false))).collect();
        if let Some(scalar) = &self.scalar {
            order.extend(scalar.entries.iter().enumerate().filter_map(|(id,e)| e.map(|e|(e.offset,id,true))));
        }
        order.sort_unstable();
        if order.first().is_some_and(|(offset, _, _)| *offset != 0) || order.is_empty() != bytes.is_empty() {
            return Err("operation map missing published prefix".into());
        }
        let (mut functions, mut assertions, mut spans) = (vec![], 0, 0);
        for (index, &(offset, id, scalar)) in order.iter().enumerate() {
            let end = order.get(index + 1).map_or(bytes.len(), |(offset, _, _)| *offset);
            if offset >= end || end > bytes.len() || offset % 4 != 0 || end % 4 != 0 {
                return Err("operation map invalid function extent".into());
            }
            let f = &self.program.functions[id];
            if scalar {
                let entry=self.scalar_entry(id).ok_or("operation map missing scalar entry")?;
                if end-offset!=entry.bytes || spans==MAX_SPANS {return Err("operation map scalar extent or span bound".into());}
                let words=self.reconstruct_scalar(id)?;verify_words(&words,&bytes[offset..end])?;
                functions.push(FunctionMap {function:id,name:&f.name,offset,end,assertion_base:assertions,assertion_count:0,
                    spans:vec![Span{offset,end,region_pc:0,pc:None,kind:Kind::ScalarLeaf}]});
                spans+=1;continue;
            }
            let mut collector = Collector { rows: vec![], limit: MAX_SPANS - spans };
            // The nonempty published entries are the original admission receipt.
            // A fresh fits() check would incorrectly count their table twice.
            let staged = self.emit_function_inner(f, (end - offset) / 4, assertions, Some(&mut collector))
                .map_err(|e| format!("operation map reconstruction: {e:?}"))?
                .ok_or("operation map reconstruction declined")?;
            verify_words(&staged.words, &bytes[offset..end])?;
            for (actual, rebuilt) in self.blocks[id].iter().zip(&staged.entries) {
                match (actual, rebuilt) {
                    (None, None) => {},
                    (Some(a), Some(b)) if a.offset == offset + b.offset && a.end == b.end => {},
                    _ => return Err("operation map reconstructed entry mismatch".into()),
                }
            }
            if self.blocks[id].len() != staged.entries.len() {
                return Err("operation map reconstructed entry count mismatch".into());
            }
            if let Some(tables) = &self.resumable {
                let published = tables.published(id);
                if published.len() != staged.resumes.len() || published.iter().zip(&staged.resumes)
                    .any(|(actual, rebuilt)| *actual != rebuilt.map_or(0, |word| arena_base + offset + word * 4)) {
                    return Err("operation map reconstructed resume mismatch".into());
                }
            }
            let assertion_end = assertions + staged.assertions.len();
            if self.assertions.get(assertions..assertion_end) != Some(staged.assertions.as_slice()) {
                return Err("operation map reconstructed assertion mismatch".into());
            }
            collector.validate(f, &staged)?;
            spans += collector.rows.len();
            for row in &mut collector.rows { row.offset += offset; row.end += offset; }
            functions.push(FunctionMap { function: id, name: &f.name, offset, end,
                assertion_base: assertions, assertion_count: staged.assertions.len(), spans: collector.rows });
            assertions = assertion_end;
        }
        if assertions != self.assertions.len() { return Err("operation map incomplete assertion coverage".into()); }
        Ok(Map { schema_version: if self.scalar.is_some() {2} else {1}, pid: std::process::id(), arena_base, code_bytes: bytes.len(),
            code_sha256: format!("{:x}", Sha256::digest(bytes)), profiled: self.profiled,
            persistent_registers: self.persistent_registers, resumable_calls: self.resumable.is_some(),
            complete: true, reconstructed_bytes_match: true, spans, functions,
            note: "Reconstructed after execution and checked against this process's published bytes, entries and assertions. Spans cover emitted bytes, including unexecuted tails; zero-word operations are explicit. Transition spans include complete native Call/Return machinery. Scalar-leaf spans cover independently reconstructed whole bodies; they do not assign body words to individual original PCs. Static size is not sampled time or retired instructions. Diagnostic I/O is not benchmark evidence." })
    }
}

fn verify_words(words: &[u32], bytes: &[u8]) -> Result<(), String> {
    if words.len() * 4 != bytes.len() || words.iter().zip(bytes.chunks_exact(4))
        .any(|(word, bytes)| word.to_le_bytes() != bytes) {
        return Err("operation map reconstructed code mismatch".into());
    }
    Ok(())
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod tests;
