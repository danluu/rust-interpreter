// Native Rust is the semantic oracle; the custom engines execute exported MIR.
#[inline(never)]
pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut result = 0u64;
    for shift in 0..64 {
        let value = seed.rotate_left(shift) ^ (1u64 << shift);
        let wide = ((value as u128) << 64) | (!value as u128);
        let counts = [
            (value as u8).count_ones(), (value as i8).count_ones(),
            (value as u16).count_ones(), (value as i16).count_ones(),
            (value as u32).count_ones(), (value as i32).count_ones(),
            value.count_ones(), (value as i64).count_ones(),
            wide.count_ones(), (wide as i128).count_ones(),
            (value as u8).count_zeros(), (value as u16).count_zeros(),
            (value as u32).count_zeros(), value.count_zeros(),
        ];
        for count in counts {
            result = result.wrapping_mul(131).wrapping_add(count as u64);
        }
    }
    result
}

fn main() {
    for seed in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(seed.parse().unwrap()));
    }
}
