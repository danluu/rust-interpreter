use std::ffi::{c_char, c_void};

unsafe extern "C" {
    fn sysctlbyname(name: *const c_char, old: *mut c_void, len: *mut usize,
                    new: *mut c_void, new_len: usize) -> i32;
}

#[inline(never)]
fn query(name: *const c_char, seed: u64) -> u64 {
    let mut value = seed as u32;
    let mut length = 4usize;
    let status = unsafe { sysctlbyname(name, (&mut value as *mut u32).cast(), &mut length,
                                       std::ptr::null_mut(), 0) };
    assert!(status == 0 || status == -1);
    assert_eq!(length, 4);
    ((status as u32 as u64) << 32) | value as u64
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut result = seed;
    for name in [c"hw.optional.arm.FEAT_AES", c"hw.optional.floatingpoint", c"hw.optional.AdvSIMD",
                 c"hw.optional.arm.FEAT_SME", c"hw.optional.arm.FEAT_SVE_B16B16",
                 c"hw.cpufamily", c"hw.optional.arm.FEAT_RUST_INTERP_MISSING"] {
        let expected = query(name.as_ptr(), seed);
        let bytes = name.to_bytes_with_nul();
        let mut stack = [0u8; 128];
        for index in 0..bytes.len() { stack[index] = bytes[index]; }
        assert_eq!(query(stack.as_ptr().cast(), seed), expected);
        let heap = bytes.to_vec();
        assert_eq!(query(heap.as_ptr().cast(), seed), expected);
        result = result.rotate_left(7) ^ expected;
    }
    result
}

pub fn detected_entry(seed: u64) -> u64 {
    let features = [std::arch::is_aarch64_feature_detected!("aes"),
                    std::arch::is_aarch64_feature_detected!("crc"),
                    std::arch::is_aarch64_feature_detected!("lse"),
                    std::arch::is_aarch64_feature_detected!("sve"),
                    std::arch::is_aarch64_feature_detected!("sha2"),
                    std::arch::is_aarch64_feature_detected!("sha3")];
    features.iter().fold(seed, |out, flag| out.rotate_left(1) ^ *flag as u64)
}

pub fn rejected_name(_: u64) -> u64 { query(c"hw.ncpu".as_ptr(), 0) }
pub fn rejected_length(_: u64) -> u64 {
    let mut value = 0u32; let mut length = 8usize;
    unsafe { sysctlbyname(c"hw.optional.arm.FEAT_AES".as_ptr(), (&mut value as *mut u32).cast(),
                         &mut length, std::ptr::null_mut(), 0) as u64 }
}
pub fn rejected_write(_: u64) -> u64 {
    let mut value = 0u32; let mut length = 4usize;
    unsafe { sysctlbyname(c"hw.optional.arm.FEAT_AES".as_ptr(), (&mut value as *mut u32).cast(),
                         &mut length, std::ptr::null_mut(), 1) as u64 }
}

// A same-named Rust function is unrelated to the foreign primitive.
mod local {
    pub fn sysctlbyname(seed: u64) -> u64 { seed.wrapping_add(19) }
}
pub fn local_entry(seed: u64) -> u64 { local::sysctlbyname(seed) }

fn main() {
    let mut args = std::env::args().skip(1);
    let mode = args.next().unwrap();
    let entry: fn(u64) -> u64 = match mode.as_str() {
        "query" => rust_interp_entry,
        "detect" => detected_entry,
        "local" => local_entry,
        _ => panic!("invalid native mode"),
    };
    for arg in args { println!("{}", entry(arg.parse().unwrap())); }
}
