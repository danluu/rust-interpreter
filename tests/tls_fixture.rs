#![feature(thread_local)]
use std::cell::Cell;
use std::collections::HashMap;
use std::hash::{BuildHasher, Hash, Hasher};
use std::sync::atomic::{AtomicU64, Ordering};

static INITIALIZATIONS: AtomicU64 = AtomicU64::new(0);
static SHARED: AtomicU64 = AtomicU64::new(41);
#[repr(align(16))]
struct Aligned(Cell<u64>);
#[thread_local]
static ALIGNED: Aligned = Aligned(Cell::new(17));
#[thread_local]
static IMMUTABLE: [u64; 3] = [13, 29, 37];
thread_local! {
    static LEFT: Cell<u64> = const { Cell::new(5) };
    static RIGHT: Cell<u64> = const { Cell::new(5) };
    static LAZY: Cell<u64> = {
        INITIALIZATIONS.fetch_add(1, Ordering::Relaxed);
        Cell::new(53)
    };
    static RECURSION: Cell<bool> = const { Cell::new(false) };
    static REENTRANT: Cell<u64> = {
        if !RECURSION.replace(true) {
            assert_eq!(REENTRANT.get(), 71);
            Cell::new(73)
        } else { Cell::new(71) }
    };
    static SHARED_REFERENCE: &'static AtomicU64 = const { &SHARED };
}

#[inline(never)]
fn change_left(value: u64) -> u64 { LEFT.replace(value) }

pub fn rust_interp_entry(seed: u64) -> u64 {
    assert_eq!(INITIALIZATIONS.load(Ordering::Relaxed), 0);
    assert_eq!(LEFT.get(), 5);
    assert_eq!(RIGHT.get(), 5);
    assert_eq!(change_left(seed), 5);
    assert_eq!(LEFT.get(), seed);
    assert_eq!(RIGHT.get(), 5);
    LEFT.with(|l| RIGHT.with(|r| assert!(!std::ptr::eq(l, r))));
    assert_eq!(LAZY.get(), 53);
    assert_eq!(LAZY.replace(seed), 53);
    assert_eq!(LAZY.get(), seed);
    assert_eq!(INITIALIZATIONS.load(Ordering::Relaxed), 1);
    assert_eq!(REENTRANT.get(), 73);
    assert_eq!(REENTRANT.get(), 73);
    assert_eq!((&ALIGNED as *const Aligned as usize) % 16, 0);
    assert_eq!(ALIGNED.0.replace(seed), 17);
    assert_eq!(ALIGNED.0.get(), seed);
    SHARED_REFERENCE.with(|shared| {
        assert!(std::ptr::eq(*shared, &SHARED));
        assert_eq!(shared.fetch_add(1, Ordering::Relaxed), 41);
    });
    assert_eq!(SHARED.load(Ordering::Relaxed), 42);

    // Random keys are intentionally not compared across native/guest runs.
    // Validate ordinary Rust hashing and collection semantics instead.
    let state = std::hash::RandomState::new();
    let clone = state.clone();
    let mut a = state.build_hasher();
    let mut b = clone.build_hasher();
    seed.hash(&mut a); seed.hash(&mut b);
    assert_eq!(a.finish(), b.finish());
    let mut map = HashMap::with_hasher(state);
    for i in 0..48u64 { assert_eq!(map.insert(i, seed.wrapping_add(i)), None); }
    for i in 0..48u64 { assert_eq!(map.get(&i), Some(&seed.wrapping_add(i))); }
    for i in (0..48u64).step_by(2) { assert_eq!(map.remove(&i), Some(seed.wrapping_add(i))); }
    let mut keys: Vec<_> = map.keys().copied().collect();
    keys.sort_unstable();
    assert_eq!(keys, (0..48u64).filter(|v| v % 2 != 0).collect::<Vec<_>>());
    seed.rotate_left(17) ^ IMMUTABLE.iter().sum::<u64>() ^ ALIGNED.0.get()
}

fn main() {
    // Exactly one seed per process: these checks exercise fresh TLS, as the VM
    // does. Do not reset the tested TLS using fixture-only guest operations.
    let seed = std::env::args().nth(1).unwrap().parse().unwrap();
    println!("{}", rust_interp_entry(seed));
}
