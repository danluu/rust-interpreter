use std::cell::Cell;
use std::sync::atomic::{AtomicU64, Ordering};
static NEXT: AtomicU64 = AtomicU64::new(100);
thread_local! {
    static VALUE: Cell<u64> = Cell::new(NEXT.fetch_add(1, Ordering::Relaxed));
    static ORDINARY: &'static AtomicU64 = const { &NEXT };
}
#[test]
fn a_first() {
    assert_eq!(VALUE.get(), 100);
    assert_eq!(VALUE.replace(999), 100);
    assert_eq!(VALUE.get(), 999);
    ORDINARY.with(|value| assert_eq!(value.load(Ordering::Relaxed), 101));
}
#[test]
fn b_second() {
    assert_eq!(NEXT.load(Ordering::Relaxed), 101);
    assert_eq!(VALUE.get(), 101);
    assert_eq!(VALUE.replace(777), 101);
    ORDINARY.with(|value| assert_eq!(value.load(Ordering::Relaxed), 102));
}
