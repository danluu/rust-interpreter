//! Exact C-string comparison to an independently supplied cwd, not a digest.
unsafe extern "C" {
    fn getcwd(buffer: *mut i8, size: usize) -> *mut i8;
    fn getenv(name: *const i8) -> *mut i8;
    fn realloc(pointer: *mut u8, size: usize) -> *mut u8;
    fn free(pointer: *mut u8);
    fn __error() -> *mut i32;
}

unsafe fn equal_path(actual: *const i8, expected: *const i8) -> bool {
    if actual.is_null() || expected.is_null() { return false; }
    let mut index = 0;
    loop {
        let a = unsafe { *actual.add(index) };
        let b = unsafe { *expected.add(index) };
        if a != b { return false; }
        if a == 0 { return true; }
        index += 1;
    }
}

pub fn rust_interp_entry(mode: u64) -> u64 {
    unsafe {
        let expected = getenv(c"RUST_INTERP_GETCWD_EXPECTED".as_ptr());
        assert!(!expected.is_null());
        let mut buffer = [0x5ai8; 4096];
        let allocated = (3..=5).contains(&mode);
        let address = if allocated { std::ptr::null_mut() }
            else if mode == 10 { 1usize as *mut i8 } else { buffer.as_mut_ptr() };
        let size = match mode { 1 | 3 => 0, 2 | 4 => 1, 5 | 11 => usize::MAX, _ => buffer.len() };
        *__error() = 71;
        let result = getcwd(address, size);
        let error = *__error() as u32 as u64;
        let mut bits = 0;
        if !result.is_null() { bits |= 1; }
        if !allocated && result == address { bits |= 2; }
        if equal_path(result, expected) { bits |= 4; }
        if buffer[4095] == 0x5a { bits |= 8; }
        if allocated && !result.is_null() {
            let grown = realloc(result.cast(), 8192);
            assert!(!grown.is_null());
            if equal_path(grown.cast(), expected) { bits |= 16; }
            free(grown);
        }
        (error << 32) | bits
    }
}

fn main() {
    let mode = std::env::args().nth(1).unwrap().parse().unwrap();
    println!("{}", rust_interp_entry(mode));
}
