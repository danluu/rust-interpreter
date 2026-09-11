pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut digest = 0u128;
    macro_rules! check {
        ($ty:ty) => {{
            let a = std::hint::black_box(seed as $ty);
            let b = std::hint::black_box(seed.rotate_left(29).wrapping_add(7) as $ty);
            for a in [a,<$ty>::MIN,<$ty>::MAX,1 as $ty,-1i8 as $ty] {
                for b in [b,0 as $ty,1 as $ty,3 as $ty,<$ty>::MIN,-1i8 as $ty] {
                    for value in [a.checked_div(b),a.checked_rem(b)] {
                        digest = digest.rotate_left(11);
                        match value {
                            Some(value) => digest ^= (value as u128) ^ (1u128<<117),
                            None => digest ^= 0x0123_4567_89ab_cdef_fedc_ba98_7654_3210,
                        }
                    }
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
