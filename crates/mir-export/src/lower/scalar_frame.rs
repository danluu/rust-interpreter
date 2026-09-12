//! Experimental scalar-only slot coloring. Aggregates, addresses and call
//! destinations retain dedicated storage. No initialization is removed.
use super::*;
use rustc_middle::mir::visit::{MutatingUseContext, NonMutatingUseContext, PlaceContext, Visitor};
use std::sync::atomic::{AtomicU64, Ordering};
static NANOS: AtomicU64 = AtomicU64::new(0);
static SAVED: AtomicU64 = AtomicU64::new(0);
static CHANGED: AtomicU64 = AtomicU64::new(0);
pub(super) const MAX_LOCALS: usize = 4096;
const MAX_EVENTS: usize = 32768;
const MAX_WORK: usize = 4_000_000;

type Set = BTreeSet<usize>;
#[derive(Default, Clone, serde::Serialize, serde::Deserialize)]
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

// Retain only the chosen local layout, not the MIR events or interference graph.
// A planned layout has passed plan's independent coloring certificate. Dedicated
// slots are reconstructed only when capture consumes this, after its bounds.
pub(super) struct ChosenLayout {
    slots: Option<Vec<Slot>>,
    shapes: Vec<(usize, usize)>,
    extent: usize,
}
impl ChosenLayout {
    fn choose(shapes: Vec<(usize, usize)>, planned: Option<(Vec<Slot>, usize)>, original_extent: usize) -> Self {
        let (slots, extent) = match planned.filter(|(_, end)| *end < original_extent) {
            Some((slots, end)) => (Some(slots), end),
            None => (None, original_extent),
        };
        Self { slots, shapes, extent }
    }

    fn into_shapes(self, slots: &[Slot], local_extent: usize) -> Vec<(usize, usize)> {
        // Preserve capture's checked reconstruction, including its overflow
        // behavior, even when scalar packing selected a smaller layout.
        let mut end = 0;
        let uncolored = self.shapes.iter().map(|&(size, align)| allocate(&mut end, size, align).unwrap()).collect();
        let (expected, extent) = match self.slots {
            Some(planned) => (planned, self.extent),
            None => (uncolored, end),
        };
        assert_eq!(extent, local_extent, "baseline local extent differs");
        assert!(expected.len() == slots.len() && expected.iter().zip(slots)
            .all(|(a, b)| a.offset == b.offset && a.size == b.size), "baseline slots differ");
        self.shapes
    }
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

fn plan(shapes: &[(usize, usize)], eligible: Vec<bool>, events: Vec<Vec<Event>>, successors: &[Vec<usize>]) -> Option<(Vec<Slot>, usize)> {
    plan_with_eligibility(shapes, eligible, events, successors, None)
}
fn plan_for_promotion(shapes: &[(usize, usize)], eligible: Vec<bool>, events: Vec<Vec<Event>>, successors: &[Vec<usize>])
    -> (Vec<bool>, Option<(Vec<Slot>, usize)>)
{
    // Entry-zero liveness can change the planner's copy, even before a later
    // work-bound decline. Promotion needs the original visitor eligibility.
    let planned = plan(shapes, eligible.clone(), events, successors);
    (eligible, planned)
}
fn plan_with_eligibility(shapes: &[(usize, usize)], mut eligible: Vec<bool>, mut events: Vec<Vec<Event>>, successors: &[Vec<usize>], eligibility: Option<&mut Vec<bool>>) -> Option<(Vec<Slot>, usize)> {
    let n = shapes.len();
    if n == 0 || n > MAX_LOCALS || events.is_empty() || events.iter().map(Vec::len).sum::<usize>() > MAX_EVENTS { return None; }
    for es in &mut events {
        for e in es { e.reads.retain(|&i| eligible[i]); e.writes.retain(|&i| eligible[i]); }
    }
    let mut input = vec![Dense::new(n); events.len()];
    let mut out = Dense::new(n);
    let mut live = Dense::new(n);
    let mut output = input.clone();
    // Existing input/output rows describe the last transfer. None distinguishes
    // an unevaluated block from a transfer whose logical work charge is zero.
    let mut transfer_work = vec![None; events.len()];
    let mut work = 0;
    loop {
        let mut changed = false;
        for b in (0..events.len()).rev() {
            out.clear();
            for &s in &successors[b] { out.union_with(&input[s]); }
            if let Some(charge) = transfer_work[b] {
                if out == output[b] {
                    // Reapply the original event-work charge even when the
                    // transfer is reused, preserving every work-bound decline.
                    work += charge;
                    if work > MAX_WORK { return None; }
                    continue;
                }
            }
            let previous_work = work;
            live.copy_from(&out);
            for e in events[b].iter().rev() {
                work += 1 + live.len() + e.reads.len();
                if work > MAX_WORK { return None; }
                for &i in &e.writes { live.remove(i); }
                for &i in &e.reads { live.insert(i); }
            }
            transfer_work[b] = Some(work - previous_work);
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
    if let Some(out) = eligibility { *out = eligible; }
    Some((slots, end))
}

pub(super) fn pack(lower: &mut Lower<'_, '_>, shapes: Vec<(usize, usize)>) -> Result<()> {
    let start = std::time::Instant::now();
    let n = lower.locals.len();
    if n > MAX_LOCALS { return Ok(()); }
    let mut eligible = Vec::new();
    for (id, _) in lower.body.local_decls.iter_enumerated() {
        let ty = lower.local_ty(id);
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
    let (eligible, planned) = plan_for_promotion(&shapes, eligible, events, &successors);
    // Keep this independent of ChosenLayout, which capture consumes first.
    lower.scalar_eligibility = Some(eligible);
    let chosen = ChosenLayout::choose(shapes, planned, old);
    if let Some(slots) = &chosen.slots {
        lower.locals = slots.clone(); lower.frame_size = chosen.extent;
        CHANGED.fetch_add(1, Ordering::Relaxed); SAVED.fetch_add((old-chosen.extent) as u64, Ordering::Relaxed);
    }
    // Capture compares this original-local extent, before caller-location and
    // anonymous temporary storage are appended to the frame.
    lower.scalar_layout = Some(chosen);
    NANOS.fetch_add(start.elapsed().as_nanos() as u64, Ordering::Relaxed);
    Ok(())
}
pub(super) fn report() {
    eprintln!("rust-interp-scalar-frames: functions={} static_bytes_saved={} seconds={:.6}", CHANGED.load(Ordering::Relaxed), SAVED.load(Ordering::Relaxed), NANOS.load(Ordering::Relaxed) as f64 / 1e9);
}

#[cfg(test)]
pub(super) fn visit_eligibility_context(eligible: &mut [bool], local: mir::Local, context: PlaceContext) {
    Uses { eligible, event: Event::default() }.visit_local(local, context,
        mir::Location { block: mir::START_BLOCK, statement_index: 0 });
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

    #[test]
    fn promotion_retains_visitor_eligibility_before_entry_zero_liveness() {
        let initial = vec![false, true];
        let events = vec![vec![event(&[1], &[])]];
        let (preserved, planned) = plan_for_promotion(&[(8, 8); 2], initial.clone(), events.clone(), &[vec![]]);
        assert_eq!(preserved, [false, true]);
        assert_eq!(planned.unwrap().1, 16); // no frame saving is required
        let mut after_liveness = vec![];
        plan_with_eligibility(&[(8, 8); 2], initial, events, &[vec![]], Some(&mut after_liveness)).unwrap();
        assert_eq!(after_liveness, [false, false]);
    }

    #[test]
    fn promotion_snapshot_survives_input_and_late_work_bound_declines() {
        let initial = vec![false, true];
        let (preserved, planned) = plan_for_promotion(&[(8, 8); 2], initial.clone(),
            vec![vec![Event::default(); MAX_EVENTS + 1]], &[vec![]]);
        assert!(planned.is_none());
        assert_eq!(preserved, initial);

        let count = 2049;
        let mut initial = vec![true; count];
        initial[0] = false;
        let active: Vec<_> = (2..count).collect();
        // Local 1 loses coloring eligibility before the simultaneous live set
        // exceeds the work bound. Promotion must still receive the old bit.
        let events = vec![vec![event(&[1], &[]), event(&[], &active), event(&active, &[])]];
        let (preserved, planned) = plan_for_promotion(&vec![(8, 8); count], initial.clone(), events, &[vec![]]);
        assert!(planned.is_none());
        assert_eq!(preserved, initial);
    }

    #[test]
    fn chosen_layout_retains_the_certified_coloring() {
        let shapes = vec![(8, 8); 3];
        let planned = plan(&shapes, vec![false, true, true],
            vec![vec![event(&[], &[1]), event(&[1], &[]), event(&[], &[2]), event(&[2], &[])]], &[vec![]]);
        let chosen = ChosenLayout::choose(shapes.clone(), planned, 24);
        // The ABI local is dedicated; the two disjoint scalar lifetimes share.
        let expected = [Slot { offset: 0, size: 8 }, Slot { offset: 8, size: 8 }, Slot { offset: 8, size: 8 }];
        assert_eq!(chosen.extent, 16);
        assert_eq!(chosen.into_shapes(&expected, 16), shapes);
    }

    #[test]
    fn non_improving_and_input_bounded_plans_keep_the_original_layout() {
        let shapes = vec![(8, 8); 3];
        // This valid plan moves local 1 after local 2 without shrinking storage.
        let non_improving = plan(&shapes, vec![false, true, false],
            vec![vec![event(&[], &[1]), event(&[1], &[])]], &[vec![]]).unwrap();
        assert_eq!(non_improving.0[1].offset, 16);
        assert_eq!(non_improving.1, 24);
        let bounded = plan(&shapes, vec![false, true, true],
            vec![vec![Event::default(); MAX_EVENTS + 1]], &[vec![]]);
        assert!(bounded.is_none());
        let expected = [Slot { offset: 0, size: 8 }, Slot { offset: 8, size: 8 }, Slot { offset: 16, size: 8 }];
        for planned in [Some(non_improving), bounded] {
            let chosen = ChosenLayout::choose(shapes.clone(), planned, 24);
            assert_eq!(chosen.into_shapes(&expected, 24), shapes);
        }
    }

    #[test]
    fn work_bounded_plan_keeps_dedicated_storage() {
        let count = 2048;
        let shapes = vec![(8, 8); count];
        let active: Vec<_> = (1..count).collect();
        let mut eligible = vec![true; count];
        eligible[0] = false;
        // Simultaneous live scalars exceed the unchanged quadratic work bound.
        let planned = plan(&shapes, eligible,
            vec![vec![event(&[], &active), event(&active, &[])]], &[vec![]]);
        assert!(planned.is_none());
        let expected: Vec<_> = (0..count).map(|i| Slot { offset: i * 8, size: 8 }).collect();
        let chosen = ChosenLayout::choose(shapes.clone(), planned, count * 8);
        assert_eq!(chosen.into_shapes(&expected, count * 8), shapes);
    }

    #[test]
    fn fallback_preserves_alignment_gaps_and_zero_sized_locals() {
        let shapes = vec![(0, 16), (3, 1), (8, 8), (0, 32), (1, 1)];
        let expected = [Slot { offset: 0, size: 0 }, Slot { offset: 0, size: 3 },
            Slot { offset: 8, size: 8 }, Slot { offset: 32, size: 0 }, Slot { offset: 32, size: 1 }];
        let chosen = ChosenLayout::choose(shapes.clone(), None, 33);
        assert_eq!(chosen.into_shapes(&expected, 33), shapes);
    }

    #[test]
    fn checked_dedicated_extent_is_deferred_until_capture() {
        // Capture may decline a body before reconstructing dedicated storage.
        // Merely retaining a plan must not move a checked-overflow panic ahead
        // of those origin/input guards, even if the colored plan would fit.
        for planned in [None, Some((vec![Slot { offset: 0, size: 1 }], 1))] {
            // Match a colored plan exactly so only the checked dedicated
            // reconstruction can fail, not a stale slot or extent assertion.
            let (actual, extent) = planned.clone().unwrap_or((vec![], 2));
            let chosen = ChosenLayout::choose(vec![(usize::MAX, 1), (1, 1)], planned, 2);
            assert!(std::panic::catch_unwind(|| chosen.into_shapes(&actual, extent)).is_err());
        }
    }

    #[test]
    fn stale_slot_and_extent_certificates_are_rejected() {
        for mutation in 0..5 {
            let chosen = ChosenLayout::choose(vec![(8, 8); 2], None, 16);
            let mut actual = vec![Slot { offset: 0, size: 8 }, Slot { offset: 8, size: 8 }];
            let mut extent = 16;
            match mutation {
                0 => actual[1].offset = 0,
                1 => actual[1].size = 7,
                2 => { actual.pop(); }
                3 => actual.push(Slot { offset: 16, size: 0 }),
                // Caller-location/scratch storage must not replace local extent.
                4 => extent = 32,
                _ => unreachable!(),
            }
            assert!(std::panic::catch_unwind(|| chosen.into_shapes(&actual, extent)).is_err(),
                "accepted stale layout mutation {mutation}");
        }
    }
}

#[path="byte_writes.rs"]
pub(super) mod byte_writes;

#[cfg(test)]
#[path = "scalar_frame_liveness_tests.rs"]
mod liveness_tests;
