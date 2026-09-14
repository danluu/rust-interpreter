//! Bounded dead register elimination for this scalar emitter's own AArch64.
//! Never removes memory accesses, stack adjustments, branches or returns.
//! An unknown encoding/CFG declines the pass and preserves the original body.
use std::collections::VecDeque;

const MAX_WORDS: usize = 65_536;
const FLAGS: u64 = 1 << 32;
const VECTOR: u64 = 1 << 33;

fn reg(n: u32, sp: bool) -> u64 { if n != 31 || sp { 1 << n } else { 0 } }

#[derive(Clone, Copy, PartialEq, Eq)]
enum Branch { None, Direct, Conditional, Return }
#[derive(Clone, Copy)]
struct Word { reads: u64, writes: u64, pure: bool, next: [usize; 2], count: usize, branch: Branch }

fn decode(w: u32, pc: usize, len: usize, return_reads: u64) -> Result<Word, &'static str> {
    let (rd, rn, rm) = (w & 31, (w >> 5) & 31, (w >> 16) & 31);
    let item = |reads, writes, pure, next: [usize; 2], count, branch| {
        if next[..count].iter().any(|&p| p >= len) { return Err("native_dead_external_edge"); }
        Ok(Word { reads, writes, pure, next, count, branch })
    };
    let ordinary = |reads, writes, pure| item(reads, writes, pure, [pc + 1, 0], 1, Branch::None);
    if w == 0xd65f03c0 {
        return item(return_reads, 0, false, [0, 0], 0, Branch::Return);
    }
    if w & 0xfc000000 == 0x14000000 {
        let delta = ((w << 6) as i32 >> 6) as i64;
        let target = usize::try_from(pc as i64 + delta).map_err(|_| "native_dead_external_edge")?;
        return item(0, 0, false, [target, 0], 1, Branch::Direct);
    }
    if w & 0xff000010 == 0x54000000 {
        if w & 15 >= 14 { return Err("native_dead_condition"); }
        let delta = ((w << 8) as i32 >> 13) as i64;
        let target = usize::try_from(pc as i64 + delta).map_err(|_| "native_dead_external_edge")?;
        return item(FLAGS, 0, false, [target, pc + 1], 2, Branch::Conditional);
    }
    if matches!(w & 0xff800000, 0xd2800000 | 0xf2800000) {
        let keep = w & 0xff800000 == 0xf2800000;
        return ordinary(if keep { reg(rd, false) } else { 0 }, reg(rd, false), true);
    }
    if matches!(w & 0xffc00000, 0xf9000000 | 0xf9400000) {
        let load = w & 0xffc00000 == 0xf9400000;
        return ordinary(reg(rn, true) | if load { 0 } else { reg(rd, false) },
                        if load { reg(rd, false) } else { 0 }, false);
    }
    // Checked external scalar reads use unsigned-offset byte/halfword/word
    // loads. Keep the access even when its value is dead; it remains a read.
    if matches!(w & 0xffc00000, 0x39400000 | 0x79400000 | 0xb9400000) {
        return ordinary(reg(rn,true),reg(rd,false),false);
    }
    // Transaction commit uses narrow stores as observable memory effects.
    if matches!(w & 0xffc00000, 0x39000000 | 0x79000000 | 0xb9000000) {
        return ordinary(reg(rn,true)|reg(rd,false),0,false);
    }
    if matches!(w & 0xff800000, 0x91000000 | 0xd1000000) {
        return ordinary(reg(rn, true), reg(rd, true), rd != 31);
    }
    if matches!(w & 0xffc00000, 0x93400000 | 0xd3400000) {
        return ordinary(reg(rn, false), reg(rd, false), true);
    }
    if w & 0xffe00000 == 0x93c00000 {
        return ordinary(reg(rn, false) | reg(rm, false), reg(rd, false), true);
    }
    if matches!(w & 0xff200000, 0x8a000000 | 0xaa000000 | 0xaa200000 | 0xca000000 |
                0x8b000000 | 0xcb000000 | 0xab000000 | 0xeb000000) {
        let flags = matches!(w & 0xff200000, 0xab000000 | 0xeb000000);
        return ordinary(reg(rn, false) | reg(rm, false), reg(rd, false) | if flags { FLAGS } else { 0 }, true);
    }
    if matches!(w & 0xffe00c00, 0x9a800000 | 0x9a800400) {
        return ordinary(reg(rn, false) | reg(rm, false) | FLAGS, reg(rd, false), true);
    }
    if matches!(w & 0xfffffc00, 0xdac00000 | 0xdac00c00 | 0xdac01000) {
        return ordinary(reg(rn, false), reg(rd, false), true);
    }
    if matches!(w & 0xffe0fc00, 0x9ac00800 | 0x9ac00c00 | 0x9ac02000 | 0x9ac02400 |
                0x9ac02800 | 0x9ac02c00 | 0x1ac02c00) {
        // AArch64 integer division does not trap. The scalar emitter's explicit
        // fault branches remain side effects, even when the quotient is dead.
        return ordinary(reg(rn, false) | reg(rm, false), reg(rd, false), true);
    }
    if matches!(w & 0xffe08000, 0x9b000000 | 0x9b008000) {
        return ordinary(reg(rn, false) | reg(rm, false) | reg((w >> 10) & 31, false), reg(rd, false), true);
    }
    if matches!(w & 0xffe0fc00, 0x9b407c00 | 0x9bc07c00) {
        return ordinary(reg(rn, false) | reg(rm, false), reg(rd, false), true);
    }
    match w {
        0x9e670120 => ordinary(reg(9, false), VECTOR, true),
        0x0e205800 | 0x0e31b800 => ordinary(VECTOR, VECTOR, true),
        0x0e013c09 => ordinary(VECTOR, reg(9, false), true),
        _ => Err("native_dead_encoding"),
    }
}

pub(crate) fn eliminate(words: &[u32]) -> Result<Vec<u32>, &'static str> {
    eliminate_inner(words, false)
}
pub(crate) fn eliminate_call(words: &[u32]) -> Result<Vec<u32>, &'static str> {
    eliminate_inner(words, true)
}
fn eliminate_inner(words: &[u32], call_frame: bool) -> Result<Vec<u32>, &'static str> {
    // Both entries preserve x4–x8/x18–x30 and SP. The Call entry also
    // preserves the caller's x0–x2 and returns its status in x9.
    let returns = (4..9).chain(18..32).fold(if call_frame { 7 | (1 << 9) } else { 1 }, |m, r| m | (1 << r));
    let len = words.len();
    if len == 0 || len > MAX_WORDS { return Err("native_dead_word_limit"); }
    let mut ops = words.iter().enumerate().map(|(pc, &w)| decode(w, pc, len, returns)).collect::<Result<Vec<_>, _>>()?;
    let mut incoming = vec![(0usize, 0usize); len];
    for (pc, op) in ops.iter().enumerate() {
        for &to in &op.next[..op.count] { incoming[to].0 += 1; incoming[to].1 = pc; }
    }
    for pc in 1..len {
        // Prune only the impossible fallthrough of an unconditional Trap. Its
        // CMP cannot be bypassed by any machine edge. No instruction is removed
        // here, and no other condition or branch feasibility is inferred.
        if ops[pc].branch == Branch::Conditional && words[pc] & 15 == 0 &&
            words[pc - 1] == 0xeb1f03ff && incoming[pc] == (1, pc - 1) {
            ops[pc].count = 1;
        }
    }
    let mut pending = vec![0usize; len];
    for op in &ops { for &to in &op.next[..op.count] { pending[to] += 1; } }
    let mut queue: VecDeque<_> = pending.iter().enumerate().filter(|(_, n)| **n == 0).map(|(pc, _)| pc).collect();
    let mut order = Vec::with_capacity(len);
    while let Some(pc) = queue.pop_front() {
        order.push(pc);
        for &to in &ops[pc].next[..ops[pc].count] {
            pending[to] -= 1;
            if pending[to] == 0 { queue.push_back(to); }
        }
    }
    if order.len() != len { return Err("native_dead_cycle"); }
    let mut reachable = vec![false; len]; reachable[0] = true;
    for &pc in &order {
        if reachable[pc] { for &to in &ops[pc].next[..ops[pc].count] { reachable[to] = true; } }
    }
    let mut live = vec![0u64; len];
    let mut dead = vec![false; len];
    for &pc in order.iter().rev() {
        let op = ops[pc];
        let out = op.next[..op.count].iter().fold(0, |m, &to| m | live[to]);
        let remove = op.pure && op.writes != 0 && op.writes & out == 0;
        live[pc] = if remove { out } else { op.reads | (out & !op.writes) };
        dead[pc] = remove && reachable[pc];
    }
    // The prefix count maps a removed target to the next retained instruction.
    // Every control transfer is retained and all displacements are repatched.
    let mut offsets = vec![0usize; len]; let mut retained = 0;
    for pc in 0..len { offsets[pc] = retained; retained += usize::from(!dead[pc]); }
    let mut compact = Vec::with_capacity(retained);
    for pc in 0..len {
        if dead[pc] { continue; }
        let mut word = words[pc];
        if matches!(ops[pc].branch, Branch::Direct | Branch::Conditional) {
            let target = offsets[ops[pc].next[0]];
            if target >= retained { return Err("native_dead_relocation"); }
            let delta = target as i64 - offsets[pc] as i64;
            let (bits, shift) = if ops[pc].branch == Branch::Direct { (26, 0) } else { (19, 5) };
            if !(-(1i64 << (bits - 1))..(1i64 << (bits - 1))).contains(&delta) { return Err("native_dead_relocation"); }
            let mask = (1u32 << bits) - 1;
            word = (word & !(mask << shift)) | (((delta as u32) & mask) << shift);
        }
        compact.push(word);
    }
    Ok(compact)
}

#[cfg(test)]
#[path = "native_dead_tests.rs"]
mod tests;
