//! Differential fixture for per-instance local types and projected places.

trait Model {
    type Word: Copy;
    fn narrow(value: u64) -> Self::Word;
    fn widen(value: Self::Word) -> u64;
}

macro_rules! model {
    ($name:ident, $word:ty) => {
        struct $name;
        impl Model for $name {
            type Word = $word;
            fn narrow(value: u64) -> Self::Word { value as $word }
            fn widen(value: Self::Word) -> u64 { value as u64 }
        }
    };
}
model!(Byte, u8);
model!(Half, u16);
model!(Word, u32);
model!(Wide, u64);

#[derive(Clone, Copy)]
#[repr(align(64))]
struct Marker;

#[repr(C)]
struct Record<T> {
    marker: Marker,
    values: [T; 3],
    tag: u8,
}

enum Choice<T> { Single(T), Pair(T, T), Empty(Marker) }

#[inline(never)]
fn exercise<M: Model>(seed: u64) -> u64 {
    let first: M::Word = M::narrow(seed);
    let mut record = Record {
        marker: Marker,
        values: [first, M::narrow(seed.rotate_left(13)), M::narrow(!seed)],
        tag: (seed >> 56) as u8,
    };
    let index = (seed % 3) as usize;
    let borrowed = &mut record;
    borrowed.values[index] = M::narrow(seed.wrapping_add(0x123456789));
    let choice = match seed % 3 {
        0 => Choice::Single(borrowed.values[1]),
        1 => Choice::Pair(borrowed.values[0], borrowed.values[2]),
        _ => Choice::Empty(borrowed.marker),
    };
    let selected = match choice {
        Choice::Single(value) => M::widen(value),
        Choice::Pair(left, right) => M::widen(left).rotate_left(7) ^ M::widen(right),
        Choice::Empty(marker) => std::mem::align_of_val(&marker) as u64,
    };
    let slice = &record.values[..];
    selected ^ M::widen(slice[index]).rotate_left(11)
        ^ M::widen(slice[(index + 1) % 3]).rotate_left(29)
        ^ M::widen(first) ^ ((record.tag as u64) << 40)
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    exercise::<Byte>(seed) ^ exercise::<Half>(seed).rotate_left(3)
        ^ exercise::<Word>(seed).rotate_left(17) ^ exercise::<Wide>(seed).rotate_left(31)
}

// Independent integer-only oracle: no associated types, aggregate layout,
// generic helper calls, enum storage, references or slice projections.
fn reference(seed: u64) -> u64 {
    let mut answer = 0;
    for (bits, shift) in [(8, 0), (16, 3), (32, 17), (64, 31)] {
        let mask = if bits == 64 { u64::MAX } else { (1u64 << bits) - 1 };
        let first = seed & mask;
        let mut second = seed.rotate_left(13) & mask;
        let mut third = !seed & mask;
        let mut current_first = first;
        let replacement = seed.wrapping_add(0x123456789) & mask;
        let (selected, next) = match seed % 3 {
            0 => { current_first = replacement; (second, second) }
            1 => { second = replacement; (current_first.rotate_left(7) ^ third, third) }
            _ => { third = replacement; (64, current_first) }
        };
        let current = match seed % 3 { 0 => current_first, 1 => second, _ => third };
        let value = selected ^ current.rotate_left(11) ^ next.rotate_left(29)
            ^ first ^ (((seed >> 56) as u8 as u64) << 40);
        answer ^= value.rotate_left(shift);
    }
    answer
}

fn main() {
    for arg in std::env::args().skip(1) {
        let seed = arg.parse().unwrap();
        let actual = rust_interp_entry(seed);
        assert_eq!(actual, reference(seed));
        println!("{actual}");
    }
}

#[test]
fn associated_types_and_projections_match_independent_integer_oracle() {
    for seed in (0..257).chain([u64::MAX, 1 << 63, 0x123456789abcdef0, 0xfedcba9876543210]) {
        assert_eq!(rust_interp_entry(seed), reference(seed), "seed={seed}");
    }
}
