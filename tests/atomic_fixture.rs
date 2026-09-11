//! Sequential atomics and real Arc ownership paths, compared with native Rust.
use std::sync::{Arc, atomic::*};

fn mix(sum: &mut u64, value: u64) { *sum = sum.rotate_left(9).wrapping_add(value); }

pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut sum = 0;
    macro_rules! integers {
        ($atomic:ty, $int:ty) => {{
            let atom = <$atomic>::new(seed as $int);
            for order in [Ordering::Relaxed, Ordering::Acquire, Ordering::Release,
                          Ordering::AcqRel, Ordering::SeqCst] {
                mix(&mut sum, atom.swap(seed.rotate_left(3) as $int, order) as u64);
                mix(&mut sum, atom.fetch_add(<$int>::MAX, order) as u64);
                mix(&mut sum, atom.fetch_sub(5, order) as u64);
                mix(&mut sum, atom.fetch_and(seed as $int, order) as u64);
                mix(&mut sum, atom.fetch_or(0x51, order) as u64);
                mix(&mut sum, atom.fetch_xor(0x78, order) as u64);
                mix(&mut sum, atom.fetch_nand(seed as $int, order) as u64);
                mix(&mut sum, atom.fetch_min(seed as $int, order) as u64);
                mix(&mut sum, atom.fetch_max(seed.rotate_left(1) as $int, order) as u64);
                for failure in [Ordering::Relaxed, Ordering::Acquire, Ordering::SeqCst] {
                    let current = atom.load(Ordering::Relaxed);
                    assert_eq!(atom.compare_exchange(current.wrapping_add(1), 7, order, failure), Err(current));
                    assert_eq!(atom.load(Ordering::Relaxed), current);
                    assert_eq!(atom.compare_exchange(current, 7, order, failure), Ok(current));
                    // Native weak CAS may fail spuriously: only compare the
                    // eventual result, never a permitted implementation choice.
                    while atom.compare_exchange_weak(7, 9, order, failure).is_err() {}
                    assert_eq!(atom.load(Ordering::Relaxed), 9);
                }
            }
            for order in [Ordering::Relaxed, Ordering::Release, Ordering::SeqCst] {
                atom.store(seed as $int, order);
                for load in [Ordering::Relaxed, Ordering::Acquire, Ordering::SeqCst] {
                    mix(&mut sum, atom.load(load) as u64);
                }
            }
        }};
    }
    integers!(AtomicU8, u8); integers!(AtomicI8, i8);
    integers!(AtomicU16, u16); integers!(AtomicI16, i16);
    integers!(AtomicU32, u32); integers!(AtomicI32, i32);
    integers!(AtomicU64, u64); integers!(AtomicI64, i64);
    integers!(AtomicUsize, usize); integers!(AtomicIsize, isize);

    let flag = AtomicBool::new(seed & 1 != 0);
    mix(&mut sum, flag.fetch_nand(true, Ordering::SeqCst) as u64);
    mix(&mut sum, flag.fetch_xor(true, Ordering::AcqRel) as u64);
    mix(&mut sum, flag.fetch_and(false, Ordering::Release) as u64);
    mix(&mut sum, flag.fetch_or(true, Ordering::Acquire) as u64);
    assert!(flag.swap(false, Ordering::Relaxed));
    assert_eq!(flag.compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire), Ok(false));

    let mut slots = [seed, seed.wrapping_add(17), seed.wrapping_sub(9)];
    let first = slots.as_mut_ptr();
    let second = unsafe { first.add(1) };
    let pointer = AtomicPtr::new(first);
    assert_eq!(pointer.swap(second, Ordering::AcqRel), first);
    assert_eq!(pointer.compare_exchange(first, first, Ordering::SeqCst, Ordering::Acquire), Err(second));
    mix(&mut sum, unsafe { *pointer.load(Ordering::Relaxed) });
    assert_eq!(pointer.compare_exchange(second, first, Ordering::Release, Ordering::Relaxed), Ok(second));

    let shared = Arc::new(AtomicU64::new(seed));
    let weak = Arc::downgrade(&shared);
    let another = Arc::clone(&shared);
    assert_eq!(Arc::strong_count(&shared), 2);
    assert_eq!(Arc::weak_count(&shared), 1);
    another.fetch_add(11, Ordering::Relaxed);
    drop(another);
    let upgraded = weak.upgrade().unwrap();
    mix(&mut sum, upgraded.load(Ordering::Acquire));
    drop(upgraded);
    assert_eq!(Arc::strong_count(&shared), 1);
    drop(shared);
    assert!(weak.upgrade().is_none());
    drop(weak);

    // Arc copy-on-write reaches the thin raw-pointer aggregate that failed
    // while lowering Nushell's existing Value mutation test.
    let mut shared = Arc::new(vec![seed, !seed]);
    let original = shared.clone();
    Arc::make_mut(&mut shared)[0] = seed.wrapping_add(29);
    assert_eq!(original[0], seed);
    assert_eq!(shared[0], seed.wrapping_add(29));
    mix(&mut sum, shared[0]);
    drop(original);
    let weak = Arc::downgrade(&shared);
    Arc::make_mut(&mut shared)[1] ^= 37;
    assert!(weak.upgrade().is_none());
    mix(&mut sum, shared[1]);

    struct CountDrop { count: Arc<AtomicUsize>, value: u64 }
    impl Drop for CountDrop {
        fn drop(&mut self) { self.count.fetch_add(1, Ordering::SeqCst); }
    }
    let count = Arc::new(AtomicUsize::new(0));
    let owner = Arc::new(CountDrop { count: count.clone(), value: seed });
    let clone = owner.clone();
    drop(owner);
    assert_eq!(count.load(Ordering::Relaxed), 0);
    mix(&mut sum, clone.value);
    drop(clone);
    assert_eq!(count.load(Ordering::Relaxed), 1);
    for order in [Ordering::Acquire, Ordering::Release, Ordering::AcqRel, Ordering::SeqCst] {
        fence(order);
        compiler_fence(order);
    }
    sum
}

fn main() {
    for value in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(value.parse().unwrap()));
    }
}
