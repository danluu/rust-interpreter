//! Retained uncached planner oracle for transient liveness-transfer reuse.
//! The function below is copied from b767335's scalar_frame.rs, with only its
//! name changed. Keep it uncached and separate from the production planner.
use super::*;

fn retained_plan(shapes: &[(usize, usize)], mut eligible: Vec<bool>, mut events: Vec<Vec<Event>>, successors: &[Vec<usize>], eligibility: Option<&mut Vec<bool>>) -> Option<(Vec<Slot>, usize)> {
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
    if let Some(out) = eligibility { *out = eligible; }
    Some((slots, end))
}

fn event(reads: &[usize], writes: &[usize]) -> Event {
    Event { reads: reads.iter().copied().collect(), writes: writes.iter().copied().collect() }
}

type Layout = Option<(Vec<(usize, usize)>, usize)>;
fn describe(plan: Option<(Vec<Slot>, usize)>) -> Layout {
    plan.map(|(slots, extent)| (slots.iter().map(|s| (s.offset, s.size)).collect(), extent))
}

fn compare(
    shapes: &[(usize, usize)], eligible: Vec<bool>, events: Vec<Vec<Event>>,
    successors: &[Vec<usize>], label: &str,
) -> (Layout, Vec<bool>) {
    // A decline must leave the caller's eligibility output untouched, even
    // when internal entry-zero liveness already changed the planner's copy.
    let mut expected_eligibility = vec![true, false, true];
    let mut actual_eligibility = expected_eligibility.clone();
    let expected = describe(retained_plan(shapes, eligible.clone(), events.clone(), successors,
        Some(&mut expected_eligibility)));
    let actual = describe(plan_with_eligibility(shapes, eligible, events, successors,
        Some(&mut actual_eligibility)));
    assert_eq!(actual, expected, "layout: {label}");
    assert_eq!(actual_eligibility, expected_eligibility, "eligibility: {label}");
    (actual, actual_eligibility)
}

#[test]
fn empty_inputs_still_evaluate_reads_and_empty_transfers() {
    let (layout, eligible) = compare(&[(8, 8); 2], vec![true; 2],
        vec![vec![event(&[1], &[])]], &[vec![]], "entry read with empty output");
    assert_eq!(layout, Some((vec![(8, 8), (0, 8)], 16)));
    assert_eq!(eligible, [true, false]);

    // The reverse sweep needs several rounds to carry the entry read through
    // the empty blocks. A completed empty transfer has a valid zero charge.
    compare(&[(8, 8); 3], vec![true; 3],
        vec![vec![event(&[2], &[])], vec![], vec![]],
        &[vec![], vec![0], vec![1]], "empty transfers with delayed propagation");
    compare(&[(0, 16), (8, 8)], vec![false, true],
        vec![vec![], vec![]], &[vec![1], vec![0]], "empty cycle");
}

#[test]
fn loops_joins_dead_stores_and_same_event_reads_match_original_planner() {
    let shapes = [(8, 8), (8, 8), (8, 8), (16, 16), (0, 32)];
    let events = vec![
        vec![event(&[], &[1]), event(&[1], &[1, 2])],
        vec![event(&[2], &[3]), event(&[], &[1])],
        vec![event(&[1, 3], &[])],
        vec![event(&[4], &[4])],
    ];
    compare(&shapes, vec![false, true, true, true, true], events,
        &[vec![1, 2], vec![1, 2], vec![], vec![3]], "join, loop, unreachable self-loop");
}

fn next(seed: &mut u64) -> usize {
    *seed ^= *seed << 13;
    *seed ^= *seed >> 7;
    *seed ^= *seed << 17;
    *seed as usize
}

#[test]
fn deterministic_cfgs_match_uncached_layouts_and_eligibility() {
    let mut seed = 0x5b91_a2d8_670c_4e3fu64;
    for case in 0..512 {
        let before = seed;
        let n = match case % 16 {
            0 => 65,
            1 => 129,
            _ => 1 + next(&mut seed) % 16,
        };
        let blocks = 1 + next(&mut seed) % 8;
        let shapes: Vec<_> = (0..n).map(|_| {
            let align = 1 << (next(&mut seed) % 6);
            let size = [0, 1, 3, 8, 16][next(&mut seed) % 5];
            (size, align)
        }).collect();
        let eligible: Vec<_> = (0..n).map(|_| next(&mut seed) % 4 != 0).collect();
        let mut events = Vec::new();
        let mut successors = Vec::new();
        for _ in 0..blocks {
            let mut block = Vec::new();
            for _ in 0..next(&mut seed) % 7 {
                let mut e = Event::default();
                for i in 0..n {
                    if next(&mut seed) % 9 == 0 { e.reads.insert(i); }
                    if next(&mut seed) % 9 == 0 { e.writes.insert(i); }
                }
                block.push(e);
            }
            events.push(block);
            successors.push((0..blocks).filter(|_| next(&mut seed) % 4 == 0).collect());
        }
        compare(&shapes, eligible, events, &successors,
            &format!("case {case}, seed {before:016x}"));
    }
}

#[test]
fn cached_transfers_preserve_exact_work_boundary_and_late_declines() {
    // 999 locals are live after the last event. There are 1,999 events, with
    // `redundant_reads` extra reads of an already-live local. Each of the two
    // sweeps costs 1,999 * 1,000 + redundant_reads. The second sweep has the
    // same empty output as the first. Entry-zero preservation then excludes
    // those 999 locals; an optional dead write of local 999 adds exactly one
    // interference-work unit. Other events contribute no interference work.
    for (redundant_reads, dead_write, expected_work, accepted) in [
        (999, true, MAX_WORK - 1, true),
        (1000, false, MAX_WORK, true),
        (1000, true, MAX_WORK + 1, false),
        (1001, false, MAX_WORK + 2, false),
    ] {
        assert_eq!(2 * (1999 * 1000 + redundant_reads) + usize::from(dead_write), expected_work);
        let mut events = vec![Event::default(); 1999];
        for e in &mut events[..redundant_reads] { e.reads.insert(0); }
        events.last_mut().unwrap().reads.extend(0..999);
        if dead_write { events[1500].writes.insert(999); }
        let (layout, eligible) = compare(&vec![(8, 8); 1000], vec![true; 1000],
            vec![events], &[vec![]], &format!("logical work {expected_work}"));
        assert_eq!(layout.is_some(), accepted, "logical work {expected_work}");
        if accepted {
            assert_eq!(layout.unwrap().1, 8000);
            assert_eq!(eligible.iter().filter(|&&yes| yes).count(), 1);
            assert!(eligible[999]);
        } else {
            assert_eq!(eligible, [true, false, true]);
        }
    }
}

#[test]
fn input_bounds_and_checked_extent_fallbacks_match_original_planner() {
    compare(&[], vec![], vec![vec![]], &[vec![]], "zero locals");
    compare(&vec![(8, 8); MAX_LOCALS + 1], vec![true; MAX_LOCALS + 1],
        vec![vec![]], &[vec![]], "local bound");
    compare(&[(8, 8)], vec![true], vec![], &[], "no blocks");
    compare(&[(8, 8)], vec![true], vec![vec![Event::default(); MAX_EVENTS + 1]],
        &[vec![]], "event bound");
    compare(&[(usize::MAX, 1), (1, 1)], vec![false; 2], vec![vec![]],
        &[vec![]], "checked dedicated extent");
}
