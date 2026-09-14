//! Bounded full-CFG register liveness and fixed per-function native assignments.
use super::*;
use std::collections::VecDeque;

const MAX_PCS: usize = 65_536;
const MAX_REGISTERS: usize = 65_536;
const MAX_WORDS: usize = 1_048_576; // 8 MiB for live-in bits, per analyzed function
const MAX_EDGES: usize = 262_144;
const MAX_OPERANDS: usize = 262_144;
const MAX_WORK: usize = 32_000_000; // word/set operations before conservative decline

pub(super) struct Liveness {
    pub(super) bits: Vec<u64>,
    pub(super) stride: usize,
    successors: Vec<Vec<usize>>,
}
impl Liveness {
    pub(super) fn at(&self, pc: usize, reg: Reg) -> bool {
        self.bits.get(pc * self.stride + reg as usize / 64)
            .is_some_and(|word| word & (1 << (reg % 64)) != 0)
    }
    pub(super) fn after(&self, pc: usize, reg: Reg) -> bool {
        self.successors.get(pc).is_some_and(|next| next.iter().any(|&n| self.at(n, reg)))
    }
}

pub(super) struct Allocation {
    pub live: Liveness,
    pub registers: Vec<Reg>,
}
impl Allocation {
    pub(super) fn pair(&self, reg: Reg) -> Option<u32> {
        self.registers.iter().position(|&r| r == reg).map(|i| 23 + i as u32 * 2)
    }
}

pub(super) fn analyze(f: &Function) -> Option<Allocation> {
    analyze_with_work(f, MAX_WORK)
}
fn analyze_with_work(f: &Function, max_work: usize) -> Option<Allocation> {
    let (live, ranked) = ranked(f, max_work)?;
    let registers = ranked.into_iter().take(3).map(|(_, r)| r).collect();
    Some(Allocation { live, registers })
}

pub(super) fn ranked(f: &Function, max_work: usize) -> Option<(Liveness, Vec<(u64, Reg)>)> {
    let n = f.code.len();
    if n == 0 || n > MAX_PCS || f.registers > MAX_REGISTERS { return None; }
    let stride = f.registers.div_ceil(64);
    let words = n.checked_mul(stride)?;
    if words > MAX_WORDS { return None; }
    let mut successors = vec![vec![]; n];
    let mut predecessors = vec![vec![]; n];
    let mut uses = vec![vec![]; n];
    let mut defs = vec![vec![]; n];
    let mut edges = 0usize;
    let mut operands = 0usize;
    let mut frequency = vec![0u64; f.registers];
    let mut starts = vec![false; n];
    starts[0] = true;
    for (pc, op) in f.code.iter().enumerate() {
        let count = match op { Op::Switch { cases, .. } => cases.len().checked_add(1)?, _ => 1 };
        edges = edges.checked_add(count)?;
        if edges > MAX_EDGES { return None; }
        successors[pc] = match op {
            Op::Jump { target } => vec![*target],
            Op::Switch { cases, otherwise, .. } => {
                let mut next: Vec<_> = cases.iter().map(|(_, target)| *target).chain([*otherwise]).collect();
                next.sort_unstable(); next.dedup(); next
            }
            Op::Return | Op::Trap { .. } => vec![],
            _ if pc + 1 < n => vec![pc + 1],
            _ => vec![],
        };
        for &next in &successors[pc] {
            predecessors.get_mut(next)?.push(pc);
            if branch(op) { starts[next] = true; }
        }
        if (branch(op) || !supported(op)) && pc + 1 < n { starts[pc + 1] = true; }
        let mut valid = true;
        crate::registers::visit_registers(op, |r| {
            if r as usize >= f.registers || operands >= MAX_OPERANDS { valid = false; return; }
            uses[pc].push(r); operands += 1;
            frequency[r as usize] += 1;
        }, |r| { defs[pc].push(r); });
        if !valid || defs[pc].iter().any(|&r| r as usize >= f.registers) { return None; }
    }
    // All blocks participate, including currently unreachable code. This is
    // may-liveness: any path to a read before a write keeps the value alive.
    let mut bits = vec![0; words];
    let mut scratch = vec![0; stride];
    let mut queued = vec![true; n];
    let mut pending: VecDeque<_> = (0..n).rev().collect();
    let mut work = 0usize;
    while let Some(pc) = pending.pop_front() {
        queued[pc] = false;
        work = work.checked_add(stride.checked_mul(successors[pc].len() + 3)?)?
            .checked_add(uses[pc].len() + defs[pc].len())?;
        if work > max_work { return None; }
        scratch.fill(0);
        for &next in &successors[pc] {
            for (out, &incoming) in scratch.iter_mut().zip(&bits[next * stride..(next + 1) * stride]) { *out |= incoming; }
        }
        for &r in &defs[pc] { scratch[r as usize / 64] &= !(1 << (r % 64)); }
        for &r in &uses[pc] { scratch[r as usize / 64] |= 1 << (r % 64); }
        if bits[pc * stride..(pc + 1) * stride] != scratch {
            bits[pc * stride..(pc + 1) * stride].copy_from_slice(&scratch);
            work = work.checked_add(predecessors[pc].len())?;
            if work > max_work { return None; }
            for &previous in &predecessors[pc] {
                if !queued[previous] { queued[previous] = true; pending.push_back(previous); }
            }
        }
    }
    let live = Liveness { bits, stride, successors };
    let mut scores = vec![0u64; f.registers];
    // Enumerate set bits at region/CFG edges rather than scanning every
    // register for every instruction. Backedges weight persistent loop state.
    for (pc, next) in live.successors.iter().enumerate() {
        for &target in next {
            if !starts[target] { continue; }
            work = work.checked_add(stride)?;
            if work > max_work { return None; }
            for (word_index, &bits) in live.bits[target * stride..(target + 1) * stride].iter().enumerate() {
                let mut bits = bits;
                while bits != 0 {
                    work = work.checked_add(1)?;
                    if work > max_work { return None; }
                    let r = word_index * 64 + bits.trailing_zeros() as usize;
                    scores[r] += if target <= pc { 16 } else { 1 };
                    bits &= bits - 1;
                }
            }
        }
    }
    let mut registers: Vec<_> = scores.iter().enumerate().filter_map(|(r, &score)|
        (score != 0 && frequency[r] >= 2).then_some((score * frequency[r], r as Reg))).collect();
    registers.sort_unstable_by_key(|&(score, r)| (std::cmp::Reverse(score), r));
    Some((live, registers))
}

#[cfg(test)]
#[path = "values_tests.rs"]
mod tests;

impl Assembler<'_> {
    pub(super) fn assigned_pair(&self, reg: Reg) -> Option<u32> {
        self.values.and_then(|v| v.pair(reg))
    }
    pub(super) fn assigned_count(&self) -> usize { self.values.map_or(0, |v| v.registers.len()) }

    pub(super) fn stack_pair(&mut self, load: bool, first: u32, second: u32, offset: usize) {
        debug_assert!(offset % 8 == 0 && offset / 8 < 64);
        self.emit((if load { 0xa9400000 } else { 0xa9000000 }) |
            ((offset as u32 / 8) << 15) | (second << 10) | (31 << 5) | first);
    }
    pub(super) fn push_pair(&mut self, first: u32, second: u32, bytes: usize) {
        debug_assert!(bytes % 16 == 0 && bytes < 512);
        let immediate = (-(bytes as i32 / 8) as u32) & 0x7f;
        self.emit(0xa9800000 | (immediate << 15) | (second << 10) | (31 << 5) | first);
    }
    pub(super) fn pop_pair(&mut self, first: u32, second: u32, bytes: usize) {
        debug_assert!(bytes % 16 == 0 && bytes < 512);
        self.emit(0xa8c00000 | ((bytes as u32 / 8) << 15) | (second << 10) | (31 << 5) | first);
    }
    pub(super) fn save_value_pairs(&mut self, load: bool, start: usize) {
        for pair in 0..self.assigned_count() {
            let lo = 23 + pair as u32 * 2;
            self.stack_pair(load, lo, lo + 1, start + pair * 16);
        }
    }
    pub(super) fn load_values(&mut self) {
        let Some(values) = self.values else { return; };
        for (index, &reg) in values.registers.iter().enumerate() {
            for high in [false, true] {
                let (base, offset) = self.reg_address(reg, high);
                let physical = 23 + index as u32 * 2 + u32::from(high);
                self.emit(0xf9400000 | (offset << 10) | (base << 5) | physical);
            }
        }
    }
    pub(super) fn initialize_heap_context(&mut self) {
        // Only external entries receive the actual host pointer/length in
        // x5/x6. Internal native edges inherit x7/x8; x5/x6 become value cache.
        // Machine-word bias arithmetic is wrapping, never a Rust pointer
        // operation. A live allocation is at most isize::MAX bytes, so its
        // virtual exclusive end TAG + length cannot overflow a 64-bit word.
        self.imm(14, crate::heap::TAG as u64);
        self.three(0xcb000000, 7, 5, 14);
        self.three(0x8b000000, 8, 6, 14);
    }
    pub(super) fn external_entry(&mut self) -> usize {
        if self.resumable { self.resumable_save_host(false); }
        else {
            self.push_pair(19, 30, 16 + self.assigned_count() * 16);
            self.save_value_pairs(false, 16);
        }
        self.mov(19, 7);
        if self.heap { self.initialize_heap_context(); }
        if self.resumable {
            self.resumable_current_frame();
            self.resumable_load_budget();
        }
        // Native callees inherit x22; only external Rust entries load memory.
        let resume = self.words.len();
        self.load_values();
        resume
    }
    pub(super) fn restore_external_values(&mut self) {
        if self.resumable { self.resumable_save_host(true); }
        else {
            self.save_value_pairs(true, 16);
            self.pop_pair(19, 30, 16 + self.assigned_count() * 16);
        }
    }
    pub(super) fn spill_values_at(&mut self, pc: usize) {
        // Continuations arrive with x0 still pointing to the current caller's
        // register array. Spill before return_pc replaces x0 with the status.
        // Fault exits only restore the host ABI: they cannot resume guest code.
        let Some(values) = self.values else { return; };
        for (index, &reg) in values.registers.iter().enumerate() {
            if values.live.at(pc, reg) {
                let lo = 23 + index as u32 * 2;
                self.raw_spill(reg, lo, lo + 1);
            }
        }
    }
    pub(super) fn tree_push_frame(&mut self) {
        let pairs = if self.tree_caller_is_region { 0 } else { self.assigned_count() };
        self.push_pair(20, 21, 64 + pairs * 16);
        self.stack_pair(false, 22, 30, 16);
        self.stack_pair(false, 0, 1, 32);
        if !self.tree_caller_is_region { self.save_value_pairs(false, 64); }
    }
}


/// Static feasibility only; neither assignment nor generated code is changed.
pub(super) fn width_census(program: &Program, profile_bytes: Option<&[u8]>) -> Result<serde_json::Value, String> {
    crate::validate(program)?;
    let profile = profile_bytes.map(|bytes| super::register_width_profile::parse(program, bytes)).transpose()?;
    let mut rows = Vec::new();
    for (id, f) in program.functions.iter().enumerate() {
        let counts = profile.as_ref().map(|p| p.functions[id].native_counts(f)).transpose()?;
        let mut row = serde_json::json!({"function":id,"name":f.name});
        if let (Some(profile), Some(counts)) = (&profile, &counts) {
            let mut reads = 0u128;
            for (op, &count) in f.code.iter().zip(counts) {
                crate::registers::visit_registers(op, |_| reads += u128::from(count), |_| {});
            }
            let narrow_count = |v:u128| u64::try_from(v).map_err(|_| "weighted census count overflow".to_string());
            row["native_operation_executions"] = narrow_count(counts.iter().map(|&v|u128::from(v)).sum())?.into();
            row["native_read_operands"] = narrow_count(reads)?.into();
            row["interpreted_operation_executions"] = narrow_count(profile.functions[id].interpreted.iter().map(|&v|u128::from(v)).sum())?.into();
        }
        let Some((live, ranked)) = ranked(f, MAX_WORK) else {
            row["declined"] = "liveness bounds".into(); rows.push(row);
            continue;
        };
        let Some(narrow) = super::register_widths::prove(f) else {
            row["declined"] = "width proof bounds".into(); rows.push(row);
            continue;
        };
        let baseline: Vec<_> = ranked.iter().take(3).map(|&(_, r)| r).collect();
        let mut packed = Vec::new();
        let mut available = 6;
        for &(_, r) in &ranked {
            let cost = if narrow[r as usize] { 1 } else { 2 };
            if cost <= available { packed.push(r); available -= cost; }
            if available == 0 { break; }
        }
        let mut baseline_reads = 0u64;
        let mut packed_reads = 0u64;
        for op in &f.code {
            crate::registers::visit_registers(op, |r| {
                baseline_reads += u64::from(baseline.contains(&r));
                packed_reads += u64::from(packed.contains(&r));
            }, |_| {});
        }
        let assignments = |registers: &[Reg]| registers.iter().map(|&r| serde_json::json!({
            "register":r,"upper_half_zero":narrow[r as usize]})).collect::<Vec<_>>();
        if let (Some(profile), Some(counts)) = (&profile, &counts) {
            let mut baseline_reads = 0u128;
            let mut packed_reads = 0u128;
            let mut baseline_live = 0u128;
            let mut packed_live = 0u128;
            for (pc, (op, &count)) in f.code.iter().zip(counts).enumerate() {
                crate::registers::visit_registers(op, |r| {
                    if baseline.contains(&r) { baseline_reads += u128::from(count); }
                    if packed.contains(&r) { packed_reads += u128::from(count); }
                }, |_| {});
                let hits = u128::from(profile.functions[id].jit_blocks[pc]);
                baseline_live += hits * baseline.iter().filter(|&&r| live.at(pc, r)).count() as u128;
                packed_live += hits * packed.iter().filter(|&&r| live.at(pc, r)).count() as u128;
            }
            for (key,value) in [("baseline_native_read_operands",baseline_reads),
                                ("packed_native_read_operands",packed_reads),
                                ("baseline_live_native_block_entries",baseline_live),
                                ("packed_live_native_block_entries",packed_live)] {
                row[key] = u64::try_from(value).map_err(|_| "weighted census count overflow")?.into();
            }
        }
        let static_fields = serde_json::json!({"registers":f.registers,
            "proven_narrow":narrow.iter().filter(|&&v| v).count(),"eligible":ranked.len(),
            "baseline":assignments(&baseline),"packed":assignments(&packed),
            "packed_native_registers":6-available,
            "baseline_static_reads":baseline_reads,"packed_static_reads":packed_reads});
        row.as_object_mut().unwrap().extend(static_fields.as_object().unwrap().clone());
        rows.push(row);
    }
    Ok(serde_json::json!({"kind":"register-width-census","schema_version":2,
        "scope":"static definitions and current liveness ranking; optional verified native operand counts; no guest execution or generated-code change",
        "limitations":"Operand counts do not model the existing intra-block cache. Live block-entry counts include internal native edges, not just actual spills. Neither is a speedup estimate.",
        "functions":rows}))
}
