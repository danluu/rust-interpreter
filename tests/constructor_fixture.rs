use constructor_dependency::{Choice, Wrapped};

pub fn rust_interp_entry(seed: u64) -> u64 {
    let wrap: fn(u64) -> Wrapped<u64> = std::hint::black_box(Wrapped);
    let some: fn(u64) -> Choice<u64> = std::hint::black_box(Choice::Some);
    let other: fn(u16) -> Choice<u64> = std::hint::black_box(Choice::Other);
    let value = wrap(seed).0.rotate_left(7);
    let selected = if seed & 1 == 0 { some(value) } else { other(seed as u16) };
    let result = match selected { Choice::Some(v) => v, Choice::Other(v) => v as u64 };
    let nested = [seed, !seed, result].into_iter().map(Wrapped).map(|v| v.0)
        .fold(0u64, |a, b| a.wrapping_add(b));
    result ^ nested
}

fn main() {
    for value in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(value.parse().unwrap()));
    }
}
