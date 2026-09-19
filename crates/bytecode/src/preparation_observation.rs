//! Bounded diagnostic elapsed intervals; nested durations are not additive.
//! Absent from ordinary builds. The trace never controls guest execution.
use std::{cell::RefCell, collections::BTreeMap, rc::Rc, time::Instant};
use serde::Serialize;

pub(crate) const MAX_BUCKETS: usize = 65_536;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum Phase {
    Constructor,
    Validation,
    JitMetadata,
    ExecutionMetadata,
    CompileFunction,
    ScalarCallees,
    ScalarFunction,
    ScalarProof,
    ScalarLowering,
    ScalarEmission,
    ScalarPublication,
    OrdinaryEmission,
    OrdinaryPublication,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize)]
pub(crate) struct Measured { pub calls: u64, pub nanos: u128 }

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub(crate) struct Snapshot {
    pub schema_version: u32,
    pub complete: bool,
    pub dropped_intervals: u64,
    pub overflowed: bool,
    pub bucket_limit: usize,
    /// (function ID, phase, count and elapsed sum). None means constructor scope.
    pub rows: Vec<(Option<usize>, Phase, Measured)>,
    pub scope: &'static str,
}

struct Recorder {
    limit: usize,
    rows: BTreeMap<(Option<usize>, Phase), Measured>,
    dropped: u64,
    overflowed: bool,
}
impl Recorder {
    fn record(&mut self, function: Option<usize>, phase: Phase, nanos: u128) {
        let key = (function, phase);
        if !self.rows.contains_key(&key) && self.rows.len() >= self.limit {
            match self.dropped.checked_add(1) {
                Some(count) => self.dropped = count,
                None => self.overflowed = true,
            }
            return;
        }
        let prior = self.rows.get(&key).copied().unwrap_or_default();
        let Some(calls) = prior.calls.checked_add(1) else { self.overflowed = true; return; };
        let Some(nanos) = prior.nanos.checked_add(nanos) else { self.overflowed = true; return; };
        self.rows.insert(key, Measured { calls, nanos });
    }
}

/// Rc confinement matches Jit ownership; only a plain Snapshot crosses threads.
#[derive(Clone)]
pub(crate) struct Trace(Rc<RefCell<Recorder>>);
impl Default for Trace {
    fn default() -> Self { Self::new(MAX_BUCKETS).unwrap() }
}
impl Trace {
    pub(crate) fn new(limit: usize) -> Option<Self> {
        (limit <= MAX_BUCKETS).then(|| Self(Rc::new(RefCell::new(Recorder {
            limit, rows: BTreeMap::new(), dropped: 0, overflowed: false,
        }))))
    }
    pub(crate) fn span(&self, function: Option<usize>, phase: Phase) -> Span {
        Span { trace: self.clone(), function, phase, started: Instant::now() }
    }
    pub(crate) fn snapshot(&self) -> Snapshot {
        let r = self.0.borrow();
        Snapshot {
            schema_version: 1, complete: r.dropped == 0 && !r.overflowed,
            dropped_intervals: r.dropped, overflowed: r.overflowed, bucket_limit: r.limit,
            rows: r.rows.iter().map(|(&(f, p), &m)| (f, p, m)).collect(),
            scope: "elapsed host intervals; phases nest and workers overlap; not CPU or recoverable command savings",
        }
    }
}

pub(crate) struct Span {
    trace: Trace,
    function: Option<usize>,
    phase: Phase,
    started: Instant,
}
impl Drop for Span {
    fn drop(&mut self) {
        let elapsed = self.started.elapsed().as_nanos();
        self.trace.0.borrow_mut().record(self.function, self.phase, elapsed);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn preparation_trace_preserves_function_and_phase_identity_without_summing_nested_scopes() {
        let t = Trace::new(4).unwrap();
        for (id, phase, ns) in [(Some(3), Phase::CompileFunction, 20),
            (Some(7), Phase::ScalarFunction, 8), (Some(7), Phase::ScalarProof, 3),
            (Some(3), Phase::CompileFunction, 10)] {
            t.0.borrow_mut().record(id, phase, ns);
        }
        let s = t.snapshot(); assert!(s.complete); assert_eq!(s.rows.len(), 3);
        assert_eq!(s.rows[0], (Some(3), Phase::CompileFunction, Measured { calls: 2, nanos: 30 }));
        assert_eq!(s.rows[1].2.nanos, 8); assert_eq!(s.rows[2].2.nanos, 3);
    }
    #[test]
    fn preparation_trace_capacity_drops_only_new_buckets_and_reports_incompleteness() {
        let t = Trace::new(1).unwrap();
        t.0.borrow_mut().record(None, Phase::Constructor, 10);
        t.0.borrow_mut().record(Some(0), Phase::ScalarProof, 3);
        t.0.borrow_mut().record(None, Phase::Constructor, 2);
        let s = t.snapshot(); assert!(!s.complete); assert_eq!(s.dropped_intervals, 1);
        assert_eq!(s.rows.len(), 1); assert_eq!(s.rows[0].2, Measured { calls: 2, nanos: 12 });
        assert!(Trace::new(MAX_BUCKETS + 1).is_none());
        let z = Trace::new(0).unwrap(); z.0.borrow_mut().record(None, Phase::Constructor, 1);
        assert!(z.snapshot().rows.is_empty()); assert!(!z.snapshot().complete);
    }
    #[test]
    fn preparation_trace_overflow_keeps_prior_counters_and_marks_the_snapshot() {
        let t = Trace::new(2).unwrap();
        t.0.borrow_mut().record(Some(1), Phase::OrdinaryEmission, u128::MAX);
        t.0.borrow_mut().record(Some(1), Phase::OrdinaryEmission, 1);
        let s = t.snapshot(); assert!(s.overflowed && !s.complete);
        assert_eq!(s.rows[0].2, Measured { calls: 1, nanos: u128::MAX });
        t.0.borrow_mut().rows.insert((Some(2), Phase::OrdinaryPublication), Measured { calls: u64::MAX, nanos: 0 });
        t.0.borrow_mut().record(Some(2), Phase::OrdinaryPublication, 1);
        assert_eq!(t.snapshot().rows[1].2, Measured { calls: u64::MAX, nanos: 0 });
        let full = Trace::new(0).unwrap(); full.0.borrow_mut().dropped = u64::MAX;
        full.0.borrow_mut().record(None, Phase::Constructor, 1);
        assert!(full.snapshot().overflowed); assert_eq!(full.snapshot().dropped_intervals, u64::MAX);
    }
    #[test]
    fn preparation_trace_spans_finish_on_error_and_unwind_without_borrowing_the_owner() {
        let t = Trace::default();
        let result: Result<(), ()> = (|| {
            let _outer = t.span(Some(2), Phase::CompileFunction);
            let _inner = t.span(Some(4), Phase::ScalarFunction); Err(())
        })(); assert!(result.is_err());
        assert_eq!(t.snapshot().rows.len(), 2);
        let u = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _span = t.span(None, Phase::Validation); panic!("deliberate diagnostic unwind");
        })); assert!(u.is_err());
        let s = t.snapshot(); assert!(s.complete); assert_eq!(s.rows.len(), 3);
        assert!(s.rows.iter().all(|r| r.2.calls == 1));
    }
    #[test]
    fn preparation_trace_snapshots_are_owned_and_worker_traces_remain_independent() {
        fn send_sync<T: Send + Sync>() {} send_sync::<Snapshot>();
        let t = Trace::default(); t.0.borrow_mut().record(None, Phase::Constructor, 4);
        let old = t.snapshot(); t.0.borrow_mut().record(None, Phase::Constructor, 3);
        assert_eq!(old.rows[0].2.nanos, 4); assert_eq!(t.snapshot().rows[0].2.nanos, 7);
        let other = std::thread::spawn(|| {
            let t = Trace::default(); t.0.borrow_mut().record(None, Phase::Constructor, 9); t.snapshot()
        }).join().unwrap();
        assert_eq!(other.rows[0].2.nanos, 9); assert_eq!(old.rows[0].2.nanos, 4);
    }
    #[test]
    fn preparation_trace_schema_names_cover_every_declared_phase_and_serialize_u128() {
        let phases = [Phase::Constructor, Phase::Validation, Phase::JitMetadata, Phase::ExecutionMetadata,
            Phase::CompileFunction, Phase::ScalarCallees, Phase::ScalarFunction, Phase::ScalarProof,
            Phase::ScalarLowering, Phase::ScalarEmission, Phase::ScalarPublication,
            Phase::OrdinaryEmission, Phase::OrdinaryPublication];
        let t = Trace::default();
        for p in phases { t.0.borrow_mut().record(Some(0), p, u128::MAX); }
        let s = t.snapshot(); assert_eq!(s.rows.len(), phases.len());
        let text = serde_json::to_string(&s).unwrap();
        assert!(text.contains("scalar_proof") && text.contains("ordinary_publication"));
        assert!(text.contains(&u128::MAX.to_string()));
    }
}
