//! Count frame initialization overwritten by arguments; never execute or edit.
use bincode::Options;
pub use rust_interp_bytecode::*;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

// Compile the retained proof directly, rather than reproducing its logic or
// inferring pointer roles from Debug strings. This does not change the VM.
#[path = "../../../crates/bytecode/src/calls.rs"]
mod calls;

#[derive(Deserialize)]
struct Profile { functions: Vec<FunctionCounts> }
#[derive(Deserialize)]
struct FunctionCounts {
    name: String,
    frame_size: usize,
    registers: usize,
    operations: Vec<String>,
    interpreted: Vec<u64>,
    jit_blocks: Vec<u64>,
    jit_block_ends: Vec<usize>,
}

#[derive(Default, Serialize)]
struct Counts {
    call_sites: u64,
    calls: u128,
    frame_bytes_without_alignment_padding: u128,
    argument_copy_bytes: u128,
    distinct_argument_bytes: u128,
    zero_gap_ranges: u128,
    frame_bytes_in_fully_overwritten_frames: u128,
    fully_overwritten_calls: u128,
}

impl Counts {
    fn add(&mut self, count: u64, frame_size: usize, copied: usize, covered: usize, gaps: usize) {
        self.call_sites += 1;
        self.calls += count as u128;
        self.frame_bytes_without_alignment_padding += count as u128 * frame_size as u128;
        self.argument_copy_bytes += count as u128 * copied as u128;
        self.distinct_argument_bytes += count as u128 * covered as u128;
        self.zero_gap_ranges += count as u128 * gaps as u128;
        if frame_size == covered {
            self.fully_overwritten_calls += count as u128;
            self.frame_bytes_in_fully_overwritten_frames += count as u128 * frame_size as u128;
        }
    }
}

#[derive(Serialize)]
struct Callee {
    id: usize,
    name: String,
    frame_size: usize,
    frame_align: usize,
    arguments: Vec<(usize, usize)>,
    merged_argument_ranges: Vec<(usize, usize)>,
    zero_ranges: Vec<(usize, usize)>,
    proven_local: Counts,
    unknown_sources: Counts,
}

fn ranges(function: &Function) -> (Vec<(usize, usize)>, Vec<(usize, usize)>) {
    let mut slots: Vec<_> = function.args.iter().filter(|s| s.size != 0)
        .map(|s| (s.offset, s.offset.checked_add(s.size).unwrap())).collect();
    slots.sort_unstable();
    let mut merged: Vec<(usize, usize)> = Vec::new();
    for (start, end) in slots {
        assert!(end <= function.frame_size);
        if let Some(last) = merged.last_mut() && start <= last.1 {
            last.1 = last.1.max(end);
        } else { merged.push((start, end)); }
    }
    let mut zero = Vec::new();
    let mut at = 0;
    for &(start, end) in &merged {
        if at < start { zero.push((at, start)); }
        at = end;
    }
    if at < function.frame_size.max(1) { zero.push((at, function.frame_size.max(1))); }
    assert_eq!(merged.iter().chain(&zero).map(|(a,b)| b-a).sum::<usize>(), function.frame_size.max(1));
    (merged, zero)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    assert_eq!(args.len(), 2, "usage: frame-initialization-census PROGRAM PROFILE");
    let bytes = std::fs::read(&args[0])?;
    assert!(bytes.len() <= 64 * 1024 * 1024);
    let program: Program = bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes)?;
    validate(&program)?;
    let profile: Profile = serde_json::from_reader(std::io::BufReader::new(std::fs::File::open(&args[1])?))?;
    assert_eq!(program.functions.len(), profile.functions.len());
    let proven = calls::local_arguments(&program);
    let mut rows: Vec<_> = program.functions.iter().enumerate().map(|(id, f)| {
        let (merged, zero) = ranges(f);
        Callee { id, name: f.name.clone(), frame_size: f.frame_size, frame_align: f.frame_align,
            arguments: f.args.iter().map(|s| (s.offset, s.size)).collect(),
            merged_argument_ranges: merged, zero_ranges: zero,
            proven_local: Counts::default(), unknown_sources: Counts::default() }
    }).collect();
    let (mut local, mut unknown) = (Counts::default(), Counts::default());
    let (mut indirect_calls, mut instructions) = (0u128, 0u128);
    let mut bins: BTreeMap<usize, Counts> = BTreeMap::new();
    for (id, (function, counts)) in program.functions.iter().zip(&profile.functions).enumerate() {
        assert_eq!(function.name, counts.name);
        assert_eq!(function.frame_size, counts.frame_size);
        assert_eq!(function.registers, counts.registers);
        for len in [counts.operations.len(), counts.interpreted.len(), counts.jit_blocks.len(), counts.jit_block_ends.len()] {
            assert_eq!(function.code.len(), len);
        }
        // Debug is used only as a complete equality check of the recorded
        // artifact, never parsed to discover opcodes, operands or pointer roles.
        assert!(function.code.iter().zip(&counts.operations).all(|(op, text)| format!("{op:?}") == *text));
        let mut frequencies = counts.interpreted.clone();
        for (pc, &count) in counts.jit_blocks.iter().enumerate() {
            if count == 0 { continue; }
            let end = counts.jit_block_ends[pc];
            assert!(pc < end && end <= function.code.len());
            for n in &mut frequencies[pc..end] { *n = n.checked_add(count).unwrap(); }
        }
        instructions += frequencies.iter().map(|&n| n as u128).sum::<u128>();
        for (pc, (op, count)) in function.code.iter().zip(frequencies).enumerate() {
            match op {
                Op::Call { function: callee, .. } if count != 0 => {
                    // Calls remain VM transitions, including inlined bodies.
                    assert_eq!(count, counts.interpreted[pc]);
                    let row = &mut rows[*callee];
                    let frame = row.frame_size.max(1);
                    let copied = row.arguments.iter().map(|(_, n)| n).sum();
                    let covered = row.merged_argument_ranges.iter().map(|(a,b)| b-a).sum();
                    let gaps = row.zero_ranges.len();
                    if proven[id][pc] {
                        local.add(count, frame, copied, covered, gaps);
                        row.proven_local.add(count, frame, copied, covered, gaps);
                        let bin = [16, 32, 64, 128, 256, 512, 1024, 4096, usize::MAX].into_iter().find(|&n| frame <= n).unwrap();
                        bins.entry(bin).or_default().add(count, frame, copied, covered, gaps);
                    } else {
                        unknown.add(count, frame, copied, covered, gaps);
                        row.unknown_sources.add(count, frame, copied, covered, gaps);
                    }
                }
                Op::CallIndirect { .. } => indirect_calls += count as u128,
                _ => {}
            }
        }
    }
    rows.retain(|r| r.proven_local.calls + r.unknown_sources.calls > 0);
    rows.sort_by_key(|r| std::cmp::Reverse(r.proven_local.distinct_argument_bytes));
    println!("{}", serde_json::to_string_pretty(&serde_json::json!({
        "status": "Typed frame-initialization census; no execution or transformation",
        "instructions": instructions, "proven_local": local, "unknown_sources": unknown,
        "indirect_calls_without_target_attribution": indirect_calls,
        "local_frame_size_bins": bins, "callees": rows,
        "alignment_padding_excluded": true, "entry_and_tls_frames_excluded": true,
        "performance_measurement": false,
        "limitation": "Logical byte counts do not predict memset cost or speedup. Avoiding zeros may require several gap fills and preserving initialized backing storage. Unknown sources and indirect calls are excluded from the candidate opportunity."
    }))?);
    Ok(())
}
