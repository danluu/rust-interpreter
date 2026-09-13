//! Every stat byte and every declared field is compared with an independent SDK C oracle.
#[repr(C)]
pub struct Stat {
    dev: i32, mode: u16, nlink: u16, ino: u64, uid: u32, gid: u32, rdev: i32,
    atime: i64, atime_nsec: i64, mtime: i64, mtime_nsec: i64, ctime: i64, ctime_nsec: i64,
    birthtime: i64, birthtime_nsec: i64, size: i64, blocks: i64, blksize: i32,
    flags: u32, generation: u32, lspare: i32, qspare: [i64; 2],
}
unsafe extern "C" {
    fn open(path: *const i8, flags: i32, ...) -> i32;
    fn close(fd: i32) -> i32;
    fn fstat(fd: i32, output: *mut Stat) -> i32;
    fn __error() -> *mut i32;
}
include!("expected.rs");

pub fn rust_interp_entry(mode: u64) -> u64 {
    unsafe {
        let fd = open(c"data.bin".as_ptr(), 0);
        assert!(fd >= 0);
        let mut storage = std::mem::MaybeUninit::<Stat>::uninit();
        let output = storage.as_mut_ptr();
        std::ptr::write_bytes(output.cast::<u8>(), 0xa5, 144);
        let supplied = match mode {
            10 => 1usize as *mut Stat,
            11 => (usize::MAX - 71) as *mut Stat,
            _ => output,
        };
        if mode == 1 { assert_eq!(close(fd), 0); }
        *__error() = 71;
        let result = fstat(if mode == 2 { -1 } else { fd }, supplied);
        let error = *__error();
        let mut byte_match = true;
        for (i, expected) in EXPECTED_BYTES.iter().enumerate() {
            let expected = if mode == 1 || mode == 2 { 0xa5 } else { *expected };
            byte_match &= *output.cast::<u8>().add(i) == expected;
        }
        let fields = [(*output).dev as u32 as u128, (*output).mode as u128,
            (*output).nlink as u128, (*output).ino as u128, (*output).uid as u128,
            (*output).gid as u128, (*output).rdev as u32 as u128,
            (*output).atime as u64 as u128, (*output).atime_nsec as u64 as u128,
            (*output).mtime as u64 as u128, (*output).mtime_nsec as u64 as u128,
            (*output).ctime as u64 as u128, (*output).ctime_nsec as u64 as u128,
            (*output).birthtime as u64 as u128, (*output).birthtime_nsec as u64 as u128,
            (*output).size as u64 as u128, (*output).blocks as u64 as u128,
            (*output).blksize as u32 as u128, (*output).flags as u128, (*output).generation as u128,
            (*output).lspare as u32 as u128, (*output).qspare[0] as u64 as u128,
            (*output).qspare[1] as u64 as u128];
        let field_match = fields == EXPECTED_FIELDS;
        let success = mode != 1 && mode != 2;
        let mut bits = 0;
        if result == if success { EXPECTED_RETURN } else { -1 } { bits |= 1; }
        if error == if success { EXPECTED_ERRNO } else { 9 } { bits |= 2; }
        if byte_match { bits |= 4; }
        if !success || field_match { bits |= 8; }
        if mode != 1 { assert_eq!(close(fd), 0); }
        bits
    }
}
fn main() {
    let mode = std::env::args().nth(1).unwrap().parse().unwrap();
    println!("{}", rust_interp_entry(mode));
}
