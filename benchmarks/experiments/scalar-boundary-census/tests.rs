use super::*;

#[test]
fn colored_overlap_and_ineligible_alias() {
    let s = |offset, size| Slot { offset, size };
    let slots = [s(0, 8), s(0, 8), s(8, 8), s(12, 8), s(24, 4), s(28, 0)];
    assert_eq!(disjoint_private(&slots, &[true, false, true, true, true, true]).unwrap(),
        [false, false, false, false, true, false]);
    assert_eq!(disjoint_private(&slots[..2], &[true, true]).unwrap(), [true, true]);
    assert!(disjoint_private(&[s(usize::MAX, 8)], &[true]).is_err());
}

#[test]
fn independent_rejection_reasons() {
    assert_eq!(reasons(false, false, false, false, 8, false),
        ["use_context_or_address_exposure", "call_operand", "aggregate_operand"]);
    assert_eq!(reasons(true, true, true, false, 8, false), ["overlapping_or_shared_storage"]);
    assert_eq!(reasons(true, true, true, true, 0, true), ["zero_or_unsupported_width", "spread_argument"]);
    assert!(reasons(true, true, true, true, 8, false).is_empty());
}

#[test]
fn bounds_and_widths_are_explicit() {
    assert!(within_bounds(4096, 100_000, 2, 3));
    for args in [(4097, 1, 0, 1), (1, 100_001, 0, 1), (1, 1, 2, 2), (1, 1, usize::MAX, usize::MAX)] {
        assert!(!within_bounds(args.0, args.1, args.2, args.3));
    }
    assert!([1, 2, 4, 8, 16].into_iter().all(width));
    assert!([0, 3, 15, 17, usize::MAX].into_iter().all(|n| !width(n)));
}

fn observation(id: usize) -> Observation {
    Observation { id, args: vec![], result: Slot { offset: 0, size: 0 }, status: "observed",
        rows: vec![], private_primitive_locals: 0, spread_argument: false, synthetic_caller_location: false }
}

#[test]
fn duplicate_names_do_not_bind_different_bodies() {
    let a = Function { name: "same".into(), frame_size: 0, frame_align: 1, registers: 0,
        args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![Op::Return] };
    let mut b = a.clone(); b.code = vec![Op::Trap { message: "different".into() }];
    let functions = [a, b];
    assert_ne!(bind(observation(0), &functions).unwrap()["function_sha256"],
        bind(observation(1), &functions).unwrap()["function_sha256"]);
    let mut wrong = observation(0); wrong.result.size = 8;
    assert!(bind(wrong, &functions).is_err());
    assert!(bind(observation(2), &functions).is_err());
}

#[test]
fn collector_exhaustion_is_rejected() {
    let mut c = Collector::default();
    let mut a = observation(0); a.rows = vec![Value::Null; MAX_ROWS];
    c.push(a).unwrap(); assert_eq!(c.remaining(), 0);
    let mut b = observation(1); b.rows.push(Value::Null);
    assert!(c.push(b).is_err());
    assert_eq!(c.remaining(), 0);
}
