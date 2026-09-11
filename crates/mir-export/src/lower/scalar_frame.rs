//! Experimental scalar-only slot coloring. Aggregates, addresses and call
//! destinations retain dedicated storage. No initialization is removed.
use super::*;
use rustc_middle::mir::visit::{MutatingUseContext, NonMutatingUseContext, PlaceContext, Visitor};
use std::sync::atomic::{AtomicU64, Ordering};
static NANOS: AtomicU64 = AtomicU64::new(0);
static SAVED: AtomicU64 = AtomicU64::new(0);
static CHANGED: AtomicU64 = AtomicU64::new(0);
const MAX_LOCALS: usize = 4096;
const MAX_EVENTS: usize = 32768;
const MAX_WORK: usize = 4_000_000;

type Set = BTreeSet<usize>;
#[derive(Default, Clone)]
struct Event { reads: Set, writes: Set }
struct Uses<'a> { eligible: &'a mut [bool], event: Event }
impl<'tcx> Visitor<'tcx> for Uses<'_> {
    fn visit_local(&mut self, local: mir::Local, context: PlaceContext, _: mir::Location) {
        let i = local.as_usize();
        match context {
            PlaceContext::NonUse(..) => {},
            PlaceContext::MutatingUse(MutatingUseContext::Store) => { self.event.writes.insert(i); },
            PlaceContext::NonMutatingUse(NonMutatingUseContext::Copy | NonMutatingUseContext::Move) => { self.event.reads.insert(i); },
            _ => { self.eligible[i] = false; self.event.reads.insert(i); },
        }
    }
}

fn allocate(end: &mut usize, size: usize, align: usize) -> Option<Slot> {
    let at = end.checked_add(align - 1)? & !(align - 1);
    *end = at.checked_add(size)?;
    Some(Slot { offset: at, size })
}

#[derive(Clone, PartialEq, Eq)]
struct Dense { words: Vec<u64>, count: usize }
impl Dense {
    fn new(n: usize) -> Self { Self { words: vec![0; n.div_ceil(64)], count: 0 } }
    fn len(&self) -> usize { self.count }
    fn clear(&mut self) { self.words.fill(0); self.count = 0; }
    fn copy_from(&mut self, other: &Self) { self.words.copy_from_slice(&other.words); self.count = other.count; }
    fn insert(&mut self, i: usize) {
        let bit = 1u64 << (i % 64); let w = &mut self.words[i / 64];
        if *w & bit == 0 { *w |= bit; self.count += 1; }
    }
    fn remove(&mut self, i: usize) {
        let bit = 1u64 << (i % 64); let w = &mut self.words[i / 64];
        if *w & bit != 0 { *w &= !bit; self.count -= 1; }
    }
    fn contains(&self, i: usize) -> bool { self.words[i / 64] & (1u64 << (i % 64)) != 0 }
    fn union_with(&mut self, other: &Self) {
        for (a, b) in self.words.iter_mut().zip(&other.words) {
            self.count += (b & !*a).count_ones() as usize; *a |= *b;
        }
    }
    fn intersect_with(&mut self, other: &Self) {
        for (a, b) in self.words.iter_mut().zip(&other.words) {
            self.count -= (*a & !b).count_ones() as usize; *a &= *b;
        }
    }
    fn iter(&self) -> impl Iterator<Item=usize> + '_ {
        self.words.iter().copied().enumerate().flat_map(|(word, mut bits)| {
            std::iter::from_fn(move || {
                if bits == 0 { return None; }
                let i = bits.trailing_zeros() as usize; bits &= bits - 1; Some(word * 64 + i)
            })
        })
    }
}

fn plan(shapes: &[(usize, usize)], mut eligible: Vec<bool>, mut events: Vec<Vec<Event>>, successors: &[Vec<usize>]) -> Option<(Vec<Slot>, usize)> {
    let n = shapes.len();
    if n == 0 || n > MAX_LOCALS || events.is_empty() || events.iter().map(Vec::len).sum::<usize>() > MAX_EVENTS { return None; }
    for es in &mut events {
        for e in es { e.reads.retain(|&i| eligible[i]); e.writes.retain(|&i| eligible[i]); }
    }
    let mut input = vec![Dense::new(n); events.len()];
    let mut out = Dense::new(n);
    let mut live = Dense::new(n);
    let mut output = input.clone();
    let mut work = 0;
    loop {
        let mut changed = false;
        for b in (0..events.len()).rev() {
            out.clear();
            for &s in &successors[b] { out.union_with(&input[s]); }
            live.copy_from(&out);
            for e in events[b].iter().rev() {
                work += 1 + live.len() + e.reads.len();
                if work > MAX_WORK { return None; }
                for &i in &e.writes { live.remove(i); }
                for &i in &e.reads { live.insert(i); }
            }
            changed |= live != input[b];
            input[b].copy_from(&live); output[b].copy_from(&out);
        }
        if !changed { break; }
    }
    // Preserve every local whose original entry zero can reach a read.
    for i in input[0].iter() { eligible[i] = false; }
    let mut mask = Dense::new(n);
    for i in 0..n { if eligible[i] { mask.insert(i); } }
    let mut simultaneous = Dense::new(n);
    let mut edges = vec![Dense::new(n); n];
    for (b, es) in events.iter().enumerate() {
        live.copy_from(&output[b]);
        for e in es.iter().rev() {
            simultaneous.copy_from(&live);
            for &i in e.reads.iter().chain(&e.writes) { simultaneous.insert(i); }
            simultaneous.intersect_with(&mask);
            work += simultaneous.len().checked_mul(simultaneous.len())?;
            if work > MAX_WORK { return None; }
            // Dead stores must interfere too; sharing them with a live value
            // would clobber that value even though the store itself is unused.
            for a in simultaneous.iter() {
                edges[a].union_with(&simultaneous); edges[a].remove(a);
            }
            for &i in &e.writes { live.remove(i); }
            for &i in &e.reads { live.insert(i); }
        }
        if live != input[b] { return None; }
    }
    let mut order: Vec<_> = (0..n).filter(|&i| eligible[i]).collect();
    order.sort_by_key(|&i| (std::cmp::Reverse(edges[i].len()), std::cmp::Reverse(shapes[i].0), i));
    let mut groups: Vec<Vec<usize>> = vec![];
    let mut group_of = vec![None; n];
    for i in order {
        let g = groups.iter().position(|g| shapes[g[0]] == shapes[i] && g.iter().all(|j| !edges[i].contains(*j)));
        let g = g.unwrap_or_else(|| { groups.push(vec![]); groups.len()-1 });
        groups[g].push(i); group_of[i] = Some(g);
    }
    let mut slots = vec![Slot { offset: 0, size: 0 }; n];
    let mut end = 0;
    for i in 0..n {
        if !eligible[i] { slots[i] = allocate(&mut end, shapes[i].0, shapes[i].1)?; }
    }
    for group in groups {
        let shape = shapes[group[0]];
        let slot = allocate(&mut end, shape.0, shape.1)?;
        for i in group { slots[i] = slot; }
    }
    // Certify the coloring independently of the greedy group selection.
    for i in 0..n {
        if slots[i].size != shapes[i].0 || slots[i].offset % shapes[i].1 != 0 { return None; }
        if eligible[i] && edges[i].iter().any(|j| group_of[i] == group_of[j]) { return None; }
    }
    Some((slots, end))
}

pub(super) fn pack(lower: &mut Lower<'_, '_>) -> Result<()> {
    let start = std::time::Instant::now();
    let n = lower.locals.len();
    if n > MAX_LOCALS { return Ok(()); }
    let mut shapes = Vec::new();
    let mut eligible = Vec::new();
    for (id, local) in lower.body.local_decls.iter_enumerated() {
        let ty = lower.mono(local.ty); let layout = lower.layout(ty)?;
        shapes.push((layout.size.bytes_usize(), layout.align.abi.bytes() as usize));
        eligible.push(id.as_usize() > lower.body.arg_count && matches!(ty.kind(), ty::Int(_) | ty::Uint(_) | ty::Float(_) | ty::Bool | ty::Char));
    }
    let mut events = vec![]; let mut successors = vec![];
    for (bb, block) in lower.body.basic_blocks.iter_enumerated() {
        let mut es = vec![];
        for (statement_index, statement) in block.statements.iter().enumerate() {
            let mut v = Uses { eligible: &mut eligible, event: Event::default() };
            v.visit_statement(statement, mir::Location { block: bb, statement_index }); es.push(v.event);
        }
        let mut v = Uses { eligible: &mut eligible, event: Event::default() };
        v.visit_terminator(block.terminator(), mir::Location { block: bb, statement_index: block.statements.len() }); es.push(v.event);
        events.push(es); successors.push(block.terminator().successors().map(|b| b.as_usize()).collect());
    }
    let old = lower.frame_size;
    if let Some((slots, end)) = plan(&shapes, eligible, events, &successors).filter(|(_, end)| *end < old) {
        lower.locals = slots; lower.frame_size = end;
        CHANGED.fetch_add(1, Ordering::Relaxed); SAVED.fetch_add((old-end) as u64, Ordering::Relaxed);
    }
    NANOS.fetch_add(start.elapsed().as_nanos() as u64, Ordering::Relaxed);
    Ok(())
}
pub(super) fn report() {
    eprintln!("rust-interp-scalar-frames: functions={} static_bytes_saved={} seconds={:.6}", CHANGED.load(Ordering::Relaxed), SAVED.load(Ordering::Relaxed), NANOS.load(Ordering::Relaxed) as f64 / 1e9);
}

#[cfg(test)]
mod tests {
    use super::*;
    fn event(reads: &[usize], writes: &[usize]) -> Event { Event { reads: reads.iter().copied().collect(), writes: writes.iter().copied().collect() } }
    fn simple(events: Vec<Vec<Event>>, successors: Vec<Vec<usize>>) -> Vec<Slot> {
        plan(&[(8,8);4], vec![false,true,true,true], events, &successors).expect("bounded model").0
    }
    #[test]
    fn disjoint_values_share_but_dead_writes_interfere() {
        let slots = simple(vec![vec![event(&[], &[1]), event(&[1], &[]), event(&[], &[2]), event(&[2], &[])]], vec![vec![]]);
        assert_eq!(slots[1].offset, slots[2].offset);
        let slots = simple(vec![vec![event(&[], &[1]), event(&[], &[2]), event(&[1], &[])]], vec![vec![]]);
        assert_ne!(slots[1].offset, slots[2].offset);
    }
    #[test]
    fn loop_carried_entry_zero_and_same_event_values_remain_distinct() {
        let slots = simple(vec![vec![event(&[], &[1])], vec![event(&[1], &[2]), event(&[2], &[])], vec![event(&[3], &[])]], vec![vec![1],vec![1,2],vec![]]);
        assert_ne!(slots[1].offset, slots[2].offset); assert_ne!(slots[3].offset, slots[1].offset); assert_ne!(slots[3].offset, slots[2].offset);
    }
    #[test]
    fn a_join_keeps_both_possible_live_values() {
        let slots = simple(vec![vec![],vec![event(&[], &[1])],vec![event(&[], &[2])],vec![event(&[1,2], &[])]],vec![vec![1,2],vec![3],vec![3],vec![]]);
        assert_ne!(slots[1].offset, slots[2].offset);
    }
}
