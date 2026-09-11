pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut digest = 0u128;
    macro_rules! check {
        ($ty:ty) => {{
            let a = std::hint::black_box(seed as $ty);
            let b = std::hint::black_box(seed.rotate_left(29).wrapping_add(7) as $ty);
            for (a,b) in [(a,b),(<$ty>::MIN,!0 as $ty),(<$ty>::MAX,1 as $ty),
                (<$ty>::MIN,1 as $ty),(<$ty>::MAX,<$ty>::MAX)] {
                for (value,overflow) in [a.overflowing_add(b),a.overflowing_sub(b),a.overflowing_mul(b)] {
                    digest = digest.rotate_left(11) ^ (value as u128) ^ ((overflow as u128) << 97);
                }
            }
        }};
    }
    check!(u8);check!(i8);check!(u16);check!(i16);check!(u32);check!(i32);
    check!(u64);check!(i64);check!(usize);check!(isize);check!(u128);check!(i128);
    (digest as u64) ^ (digest >> 64) as u64
}
fn main() {
    for arg in std::env::args().skip(1) { println!("{}",rust_interp_entry(arg.parse().unwrap())); }
}
