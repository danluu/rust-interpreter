//! Guest-owned mutable state and initializer relocations, checked against Rust.
use std::cell::UnsafeCell;
use std::sync::atomic::{AtomicU64, Ordering};

#[repr(align(64))]
struct Shared(UnsafeCell<u64>);
unsafe impl Sync for Shared {}
static CELL: Shared = Shared(UnsafeCell::new(7));
static ATOMIC: AtomicU64 = AtomicU64::new(19);
static mut NUMBER: u64 = 31;
static IMMUTABLE: u64 = 113;

struct Link { value: AtomicU64, next: &'static Link }
static LEFT: Link = Link { value: AtomicU64::new(13), next: &RIGHT };
static RIGHT: Link = Link { value: AtomicU64::new(17), next: &LEFT };
static REFERENCE: &Link = &LEFT;

struct Pointer(UnsafeCell<*const u64>);
unsafe impl Sync for Pointer {}
static POINTER: Pointer = Pointer(UnsafeCell::new(&IMMUTABLE));
static mut SLICE: &mut [u64] = &mut [5, 11];

#[inline(never)]
fn read_cell() -> u64 { unsafe { *CELL.0.get() } }

pub fn rust_interp_entry(seed: u64) -> u64 {
    assert_eq!(read_cell(), 7);
    assert_eq!(ATOMIC.load(Ordering::Relaxed), 19);
    assert_eq!(unsafe { *(&raw const NUMBER) }, 31);
    assert_eq!(CELL.0.get() as usize % 64, 0);
    assert_eq!(LEFT.value.load(Ordering::Relaxed), 13);
    assert_eq!(RIGHT.value.load(Ordering::Relaxed), 17);
    assert!(std::ptr::eq(REFERENCE, &LEFT));
    assert!(std::ptr::eq(LEFT.next.next, &LEFT));
    assert_eq!(unsafe { **POINTER.0.get() }, IMMUTABLE);

    unsafe {
        *CELL.0.get() = seed;
        *(&raw mut NUMBER) = !seed;
        *POINTER.0.get() = &raw const NUMBER;
    }
    let mut sum = read_cell() ^ unsafe { **POINTER.0.get() };
    sum = sum.wrapping_add(ATOMIC.fetch_add(seed, Ordering::SeqCst));
    LEFT.next.value.fetch_xor(seed, Ordering::AcqRel);
    sum ^= RIGHT.value.load(Ordering::Acquire);
    unsafe {
        let values = &mut *(&raw mut SLICE);
        assert_eq!(*values, [5, 11]);
        values[0] = seed;
        values[1] = seed.rotate_left(9);
        sum ^= values[0].wrapping_add(values[1]);
        values.copy_from_slice(&[5, 11]);
    }
    // Freeing the last ordinary allocation must preserve all static bytes.
    for i in 0..3 {
        let allocated = Box::new(seed.wrapping_add(i));
        assert_ne!((&*allocated as *const u64), CELL.0.get().cast_const());
        sum ^= *allocated;
        drop(allocated);
        assert_eq!(read_cell(), seed);
        assert_eq!(RIGHT.value.load(Ordering::Relaxed), 17 ^ seed);
    }
    // Native evaluates the input sequence in one process. Reset exactly the
    // initial state so each native input also checks initializer semantics.
    unsafe {
        *CELL.0.get() = 7;
        *(&raw mut NUMBER) = 31;
        *POINTER.0.get() = &IMMUTABLE;
    }
    ATOMIC.store(19, Ordering::Relaxed);
    RIGHT.value.store(17, Ordering::Relaxed);
    sum
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
