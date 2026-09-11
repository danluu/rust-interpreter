#![feature(core_intrinsics)]
#![allow(internal_features)]

#[inline(never)]
fn mix(a: u64, b: u64) -> u64 {
    a.wrapping_mul(0x9e3779b97f4a7c15).rotate_left(17) ^ b
}

#[inline(never)]
fn sum(bytes: &[u8]) -> u64 {
    let mut total = 0;
    let mut i = 0;
    while i < bytes.len() {
        total = mix(total, bytes[i] as u64);
        i += 1;
    }
    total
}

#[inline(never)]
fn generic<T: Copy>(a: T, b: T, choose: bool) -> T {
    if choose { a } else { b }
}

#[inline(never)]
fn factorial(n: u64) -> u64 {
    if n == 0 { 1 } else { n * factorial(n - 1) }
}

#[inline(never)]
fn callback<const N: u64>(a: u64) -> u64 {
    a.wrapping_mul(N).rotate_right(N as u32)
}

#[inline(never)]
fn choose_callback(a: u64) -> fn(u64) -> u64 {
    if a & 1 == 0 { callback::<7> } else { callback::<13> }
}

const CALLBACKS: [fn(u64) -> u64; 2] = [callback::<3>, callback::<11>];

#[inline(never)]
fn apply_callback(f: fn(u64) -> u64, a: u64) -> u64 {
    f(a)
}

enum Choice {
    A(u64),
    B(u8, u64),
    C,
}

struct Guard<'a>(&'a mut u64);
impl Drop for Guard<'_> {
    fn drop(&mut self) {
        *self.0 = self.0.wrapping_add(7);
    }
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut dropped = seed;
    {
        let _guard = Guard(&mut dropped);
    }
    let mut bytes = [1u8, 2, 3, 4, 5, 6, 7, 8];
    bytes[(seed % 8) as usize] = seed as u8;
    let input = [seed as u16, (seed >> 16) as u16];
    let mut copied = [0u16; 2];
    unsafe {
        std::ptr::copy_nonoverlapping(input.as_ptr(), copied.as_mut_ptr(), 2);
    }
    let pair = (seed as i8, seed as i16);
    let sign = ((pair.0 as i64 >> 2) / 3) as u64;
    let chosen = generic(seed, !seed, seed & 1 == 0);
    let option = if seed & 2 == 0 { Some(chosen) } else { None };
    let choice = match seed % 3 {
        0 => Choice::A(seed),
        1 => Choice::B(seed as u8, chosen),
        _ => Choice::C,
    };
    let value = match choice {
        Choice::A(n) => n,
        Choice::B(a, b) => a as u64 ^ b,
        Choice::C => 99,
    };
    let mut result = sum(&bytes) ^ sum(b"persistent bytecode") ^ sign ^ value;
    let generated: [u8; 17] = std::array::from_fn(|i| seed.wrapping_add(i as u64 * 3) as u8);
    result ^= sum(&generated);
    let selected_slice = &copied[..(seed % 3) as usize];
    result = mix(result, std::mem::size_of_val(selected_slice) as u64);
    result = mix(result, std::mem::align_of_val(selected_slice) as u64);
    let selected_string = &"slice-layout"[..(seed % 12) as usize];
    result = mix(result, std::mem::size_of_val(selected_string) as u64);
    let pointer = bytes.as_ptr().wrapping_offset(4).wrapping_offset(-3);
    result = mix(result, unsafe { *pointer } as u64);
    result = mix(result, apply_callback(choose_callback(seed), seed));
    let f: unsafe fn(u64) -> u64 = CALLBACKS[(seed % 2) as usize];
    result = mix(result, unsafe { f(seed) });
    let comparison = [seed as u8, (seed >> 8) as u8, 3, 4, 5, 6, 7, 8];
    for length in [0, 1, 3, 8] {
        result = mix(result, (bytes[..length].cmp(&comparison[..length]) as i8) as u64);
        result = mix(result, (comparison[..length] == bytes[..length]) as u64);
    }
    result ^= option.unwrap_or(17) ^ factorial(seed % 10);
    let wide = (seed as u128).wrapping_mul(0xfedcba98765432100123456789abcdef);
    macro_rules! extrema {
        ($t:ty) => {{
            let a = wide as $t;
            let b = !a;
            let divisible = (a / 3) * 3;
            let quotient = unsafe { std::intrinsics::exact_div(divisible, 3) } as u128;
            result = mix(result, quotient as u64 ^ (quotient >> 64) as u64);
            let low = a.min(b) as u128;
            let high = a.max(b) as u128;
            result = mix(result, low as u64 ^ (low >> 64) as u64);
            result = mix(result, high as u64 ^ (high >> 64) as u64);
            result = mix(result, a.min(a) as u64);
            result = mix(result, a.max(a) as u64);
            for value in [a.saturating_add(a), a.saturating_sub(b),
                          a.saturating_add(1), a.saturating_sub(1),
                          <$t>::MAX.saturating_add(a), <$t>::MIN.saturating_sub(a)] {
                let value = value as u128;
                result = mix(result, value as u64 ^ (value >> 64) as u64);
            }
        }};
    }
    extrema!(u8); extrema!(i8); extrema!(u16); extrema!(i16);
    extrema!(u32); extrema!(i32); extrema!(u64); extrema!(i64);
    extrema!(u128); extrema!(i128); extrema!(usize); extrema!(isize);
    result
        ^ ((wide >> 64) as u64)
        ^ (wide as u64)
        ^ dropped
        ^ copied[0] as u64
        ^ ((copied[1] as u64) << 16)
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
