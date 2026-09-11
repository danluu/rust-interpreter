use std::marker::PhantomData;
use std::sync::atomic::{AtomicU64, Ordering};

static EVENTS: AtomicU64 = AtomicU64::new(0);
struct Zero;
impl Drop for Zero {
    fn drop(&mut self) { EVENTS.fetch_add(1, Ordering::Relaxed); }
}
#[repr(align(128))]
struct AlignedZero;
fn make_zero() -> Zero { EVENTS.fetch_add(3, Ordering::Relaxed); Zero }
fn consume_zero(_zero: Zero, value: u64, _unit: (), _marker: PhantomData<u128>) -> u64 {
    value ^ EVENTS.load(Ordering::Relaxed)
}
fn aligned_argument(zero: AlignedZero, value: u64) -> u64 {
    assert_eq!((&zero as *const AlignedZero as usize) % 128, 0);
    value.rotate_left(3)
}

#[derive(Clone, Copy)]
#[repr(align(32))]
struct Payload { wide: u128, words: [u64; 3], tail: u8 }
trait Seed { fn seed() -> u64; }
struct Left;
struct Right;
impl Seed for Left { fn seed() -> u64 { 31 } }
impl Seed for Right { fn seed() -> u64 { 73 } }
fn factory<T: Seed>() -> fn(u64) -> u64 { |value| value.wrapping_add(T::seed()) }

const CONSTANT: fn(u64) -> u64 = |value| value.rotate_left(9);
static TABLE: [fn(u64) -> u64; 2] = [|value| value.wrapping_add(19), |value| value ^ 23];

struct Counted(u64);
impl Drop for Counted {
    fn drop(&mut self) { EVENTS.fetch_add(self.0, Ordering::Relaxed); }
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    EVENTS.store(0, Ordering::Relaxed);
    let closure = std::hint::black_box(|a: u64, b: u128| b.rotate_left(17) ^ a as u128);
    let callback: fn(u64, u128) -> u128 = closure;
    let mut result = callback(seed, (seed as u128) << 64 | !seed as u128);
    let unsafe_callback: unsafe fn(u64, u128) -> u128 = closure;
    result ^= unsafe { unsafe_callback(!seed, seed as u128) };

    let zero_args: fn() -> u64 = std::hint::black_box(|| 17);
    result ^= zero_args() as u128;
    result ^= CONSTANT(seed) as u128;
    for callback in TABLE { result = result.rotate_left(7) ^ callback(seed) as u128; }
    for callback in [factory::<Left>(), factory::<Right>()] {
        result = result.rotate_left(11) ^ callback(seed) as u128;
    }

    let aggregate: fn((), Payload, [u64; 3], ()) -> Payload = |(), mut payload, words, ()| {
        payload.wide = payload.wide.wrapping_add(words[0] as u128);
        payload.words[1] ^= words[1];
        payload.tail = payload.tail.wrapping_add(words[2] as u8);
        payload
    };
    let payload = aggregate((), Payload { wide: result, words: [seed, !seed, 29], tail: 251 },
        [seed, seed.rotate_left(5), seed.rotate_right(3)], ());
    result ^= payload.wide ^ payload.words[1] as u128 ^ payload.tail as u128;

    // A tuple parameter remains one argument after RustCall's outer tuple is
    // spread. Zero-sized fields inside the tuple must not flatten it further.
    let tuple: fn((u64, (), u128)) -> u128 = |(a, (), b)| b.wrapping_add(a as u128);
    result ^= tuple((seed, (), result));

    let consume: fn(Zero, u64, (), PhantomData<u128>) -> u64 = std::hint::black_box(consume_zero);
    result ^= consume(make_zero(), seed, (), PhantomData) as u128;
    assert_eq!(EVENTS.load(Ordering::Relaxed), 4);
    let aligned: fn(AlignedZero, u64) -> u64 = aligned_argument;
    result ^= aligned(AlignedZero, seed) as u128;

    let returning_zero: fn(u64) -> Zero = |value| {
        EVENTS.fetch_add(value & 7, Ordering::Relaxed);
        Zero
    };
    drop(returning_zero(seed));
    let expected = 5 + (seed & 7);
    assert_eq!(EVENTS.load(Ordering::Relaxed), expected);

    // Captured ZSTs are still ordinary FnOnce calls, with their destructor
    // effects preserved; they are never reclassified as non-capturing.
    let captured = Zero;
    let once = move || { drop(captured); EVENTS.fetch_add(2, Ordering::Relaxed); };
    once();
    let alignment = AlignedZero;
    let once = move |value: u64| {
        assert_eq!((&alignment as *const AlignedZero as usize) % 128, 0);
        value ^ 97
    };
    result ^= once(seed) as u128;
    let expected = expected + 3;
    assert_eq!(EVENTS.load(Ordering::Relaxed), expected);

    let mut slot = std::mem::MaybeUninit::<Counted>::uninit();
    slot.write(Counted((seed & 15) + 1));
    let destroy: unsafe fn(*mut u8) = |pointer| unsafe {
        std::ptr::drop_in_place(pointer.cast::<Counted>());
    };
    unsafe { destroy(slot.as_mut_ptr().cast()); }
    let expected = expected + (seed & 15) + 1;
    assert_eq!(EVENTS.load(Ordering::Relaxed), expected);

    let shared = |(): (), a: u64, (): ()| a.wrapping_add(101);
    let dynamic: &dyn Fn((), u64, ()) -> u64 = &shared;
    result ^= dynamic((), seed, ()) as u128;
    result ^= expected as u128;
    result as u64 ^ (result >> 64) as u64
}

fn main() {
    for seed in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(seed.parse().unwrap()));
    }
}
