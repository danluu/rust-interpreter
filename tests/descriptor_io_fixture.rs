//! Raw native/guest ABI comparison; each process runs in its own owned cwd.
unsafe extern "C" {
    fn open(path: *const i8, flags: i32, ...) -> i32;
    fn write(fd: i32, bytes: *const u8, size: usize) -> isize;
    fn close(fd: i32) -> i32;
    fn fcntl(fd: i32, command: i32, ...) -> i32;
    fn __error() -> *mut i32;
}

pub fn rust_interp_entry(phase: u64) -> u64 {
    unsafe {
        let flags = match phase { 0 => 1 | 0x200 | 0x800, 1 => 1 | 0x8, _ => 1 | 0x400 } | 0x1000000;
        *__error() = 71;
        let fd = open(c"descriptor-data.bin".as_ptr(), flags, 0o640i32);
        assert!(fd >= 0);
        let mut status = *__error() as u32 as u64;
        let bytes = [0, 255, phase as u8, 0, 128, 42];
        assert_eq!(write(fd, bytes.as_ptr(), bytes.len()), bytes.len() as isize);
        status = status.rotate_left(7) ^ *__error() as u32 as u64;
        assert_eq!(write(fd, std::ptr::null(), 0), 0);
        let flags = fcntl(fd, 1);
        assert_eq!(flags, 1);
        status = status.rotate_left(7) ^ *__error() as u32 as u64;
        assert_eq!(close(fd), 0);
        assert_eq!(fcntl(fd, 1), -1);
        assert_eq!(*__error(), 9);
        assert_eq!(close(fd), -1);
        assert_eq!(*__error(), 9);
        assert_eq!(write(fd, bytes.as_ptr(), 1), -1);
        assert_eq!(*__error(), 9);
        assert_eq!(open(c"nonexistent-parent/no-file".as_ptr(), 0), -1);
        status = status.rotate_left(7) ^ *__error() as u32 as u64;
        let fd = open(c"descriptor-data.bin".as_ptr(), 0);
        assert!(fd >= 0);
        assert_eq!(write(fd, bytes.as_ptr(), 1), -1);
        assert_eq!(*__error(), 9);
        assert_eq!(close(fd), 0);
        status
    }
}

fn main() {
    let phase = std::env::args().nth(1).unwrap().parse().unwrap();
    println!("{}", rust_interp_entry(phase));
}
