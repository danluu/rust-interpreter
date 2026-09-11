static DATA: [u64; 4] = [3, 17, 0x8123_4567_89ab_cdef, u64::MAX];
const BEFORE_DATA: *const u8 = DATA.as_ptr().cast::<u8>().wrapping_sub(1);
const AFTER_DATA: *const u64 = DATA.as_ptr().wrapping_add(3);
static mut WRAPPED: *const u8 = BEFORE_DATA;
const BEFORE_WRAPPED: *const u8 = (&raw const WRAPPED).cast::<u8>().wrapping_sub(1);

#[inline(never)]
fn plus(seed: u64) -> u64 { seed.wrapping_add(29) }
const PLUS: fn(u64) -> u64 = plus;

#[inline(never)]
fn arguments(value: u128, flag: bool, function: fn(u64) -> u64, data: &[u64], unit: ()) -> u64 {
    let () = unit;
    assert!(flag);
    assert_eq!(data.len(), 4);
    function(value as u64) ^ (value >> 64) as u64 ^ data[2]
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut digest = 0u128;
    macro_rules! integer {
        ($ty:ty) => {{
            let value = std::hint::black_box(seed as $ty);
            let a = value.wrapping_add(<$ty>::MIN);
            let b = value.wrapping_sub(<$ty>::MAX);
            let c = value.wrapping_mul(-7i8 as $ty);
            let less = value < (97 as $ty);
            digest = digest.rotate_left(11) ^ (a as u128) ^ (b as u128).rotate_left(7)
                ^ (c as u128).rotate_left(29) ^ (less as u128);
        }};
    }
    integer!(u8); integer!(i8); integer!(u16); integer!(i16);
    integer!(u32); integer!(i32); integer!(u64); integer!(i64);
    integer!(usize); integer!(isize); integer!(u128); integer!(i128);

    let fraction = (seed & 1023) as f64;
    digest ^= (fraction * -0.0f64).to_bits() as u128;
    digest ^= (fraction + -4.25f64).to_bits() as u128;
    digest ^= ((fraction as f32) * -0.0f32).to_bits() as u128;
    digest ^= ((fraction as f32) + 7.125f32).to_bits() as u128;
    digest ^= (std::hint::black_box(seed as u32) == ('\u{10ffff}' as u32)) as u128;

    // Const-evaluated pointers can carry a wrapped relative offset. Compare
    // addresses only; the out-of-allocation value is never dereferenced.
    assert_eq!(BEFORE_DATA, DATA.as_ptr().cast::<u8>().wrapping_sub(1));
    assert_eq!(BEFORE_DATA.wrapping_add(1), DATA.as_ptr().cast::<u8>());
    assert!(BEFORE_DATA == std::hint::black_box(DATA.as_ptr()).cast::<u8>().wrapping_sub(1));
    assert_eq!(BEFORE_WRAPPED.wrapping_add(1), (&raw const WRAPPED).cast::<u8>());
    assert_eq!(unsafe { WRAPPED }, BEFORE_DATA);
    assert_eq!(AFTER_DATA, DATA.as_ptr().wrapping_add(3));
    digest ^= unsafe { *AFTER_DATA } as u128;
    assert!(std::ptr::fn_addr_eq(PLUS, plus as fn(u64) -> u64));
    assert!(std::ptr::null::<u8>().is_null());
    digest ^= PLUS(seed) as u128;
    // Address consumers still need storage, including wide and aggregate
    // arguments. Slice constants retain their data allocation and metadata.
    digest ^= arguments(0xfedc_ba98_7654_3210_0123_4567_89ab_cdef, true, PLUS, &DATA, ()) as u128;
    digest ^= arguments(seed as u128, true, PLUS, &[3, 17, 0x8123_4567_89ab_cdef, u64::MAX], ()) as u128;
    (digest as u64) ^ (digest >> 64) as u64
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
