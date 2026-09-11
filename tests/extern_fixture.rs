#![feature(core_intrinsics)]

unsafe extern "C" {
    #[link_name = "getpid"]
    fn host_pid() -> i32;
    #[link_name = "abs"]
    fn host_abs(value: i32) -> i32;
}

#[inline(never)]
fn foreign_leaf(mode: u64) -> u64 {
    if mode == 0 { 17 } else if unsafe { host_pid() } > 0 { 1 } else { 0 }
}

// Keep enough caller work for the inliner's 50% whole-program growth bound.
// This is a correctness fixture, not a runtime benchmark.
pub fn entry(mode: u64) -> u64 {
    let value = foreign_leaf(mode);
    let low = mode & 0xff;
    let middle = (mode >> 8) & 0xff;
    let high = (mode >> 16) & 0xff;
    value + (low ^ low) + (middle ^ middle) + (high ^ high)
}

// A Rust function with the same name as an implemented foreign primitive.
fn abort(value: u64) -> u64 { value.wrapping_add(23) }
pub fn local_name(value: u64) -> u64 { abort(value) }

#[inline(never)]
fn argument(mode: u64) -> i32 {
    if mode == 7 { panic!("ARGUMENT_BEFORE_FOREIGN_CALL"); }
    mode as i32
}
pub fn argument_order(mode: u64) -> i32 { unsafe { host_abs(argument(mode)) } }

pub fn indirect() -> u64 {
    let callback: unsafe extern "C" fn() -> i32 = host_pid;
    u64::from(unsafe { callback() } > 0)
}

unsafe fn try_callback(data: *mut u8) { unsafe { *data = 5; } }
unsafe fn catch_callback(data: *mut u8, _: *mut u8) { unsafe { *data = 99; } }

#[inline(never)]
fn intrinsic_leaf(mode: u64) -> u64 {
    if mode == 0 { return 31; }
    let mut data = 0u8;
    let caught = unsafe {
        core::intrinsics::catch_unwind(try_callback, &raw mut data, catch_callback)
    };
    if caught { 99 } else { data as u64 }
}

pub fn intrinsic_entry(mode: u64) -> u64 {
    let value = intrinsic_leaf(mode);
    // As above, leave enough scalar caller work for bounded leaf inlining.
    let a = mode & 0xff;
    let b = (mode >> 8) & 0xff;
    let c = (mode >> 16) & 0xff;
    let d = (mode >> 24) & 0xff;
    let e = (mode >> 32) & 0xff;
    let f = (mode >> 40) & 0xff;
    value + (a ^ a) + (b ^ b) + (c ^ c) + (d ^ d) + (e ^ e) + (f ^ f)
}

#[inline(never)]
fn checked_data(mode: u64, data: *mut u8) -> *mut u8 {
    if mode == 7 { panic!("ARGUMENT_BEFORE_INTRINSIC_CALL"); }
    data
}
pub fn intrinsic_argument_order(mode: u64) -> u64 {
    let mut data = 0u8;
    unsafe {
        core::intrinsics::catch_unwind(try_callback, checked_data(mode, &raw mut data), catch_callback);
    }
    data as u64
}

#[cfg(test)]
mod tests {
    #[test]
    fn cold() {
        assert_eq!(super::entry(0), 17);
        assert_eq!(super::local_name(3), 26);
    }
    #[test]
    fn hot() { assert_eq!(super::entry(1), 1); }
    #[test]
    fn argument() { assert_eq!(super::argument_order(8), 8); }
    #[test]
    fn intrinsic_cold() { assert_eq!(super::intrinsic_entry(0), 31); }
    #[test]
    fn intrinsic_hot() { assert_eq!(super::intrinsic_entry(1), 5); }
    #[test]
    fn intrinsic_argument() { assert_eq!(super::intrinsic_argument_order(8), 5); }
}
