#![feature(signed_bigint_helpers)]

fn mix(state: &mut u128, low: u128, high: u128) {
    *state = state.rotate_left(17).wrapping_add(low) ^ high.rotate_right(29);
}

pub fn rust_interp_entry(seed: u64) -> u128 {
    let wide = ((seed as u128) << 64) | (seed.rotate_left(23) as u128);
    let mut result = wide;
    macro_rules! check {
        ($ty:ty) => {{
            let values: [$ty; 6] = [0, 1, <$ty>::MIN, <$ty>::MAX, wide as $ty, !wide as $ty];
            for i in 0..values.len() {
                for j in 0..values.len() {
                    let (low, high) = values[i].carrying_mul_add(
                        values[j], values[(i + j) % values.len()], values[(i * 3 + j) % values.len()],
                    );
                    mix(&mut result, low as u128, high as u128);
                }
            }
            for value in [<$ty>::MIN, <$ty>::MAX] {
                let (low, high) = value.carrying_mul_add(value, value, value);
                mix(&mut result, low as u128, high as u128);
            }
        }};
    }
    check!(u8); check!(u16); check!(u32); check!(u64); check!(u128); check!(usize);
    check!(i8); check!(i16); check!(i32); check!(i64); check!(i128); check!(isize);
    let callback: fn(u64, u64, u64, u64) -> (u64, u64) = std::hint::black_box(u64::carrying_mul_add);
    let (low, high) = callback(seed, seed.rotate_left(7), !seed, seed >> 1);
    mix(&mut result, low as u128, high as u128);
    result
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
