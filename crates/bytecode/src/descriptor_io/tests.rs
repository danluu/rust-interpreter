use super::*;
use crate::{Engine, Function, Slot, VERSION, execute_with_engine};

fn memory() -> Memory {
    Memory { bytes: vec![0; 8192].into(), heap: crate::heap::Heap::default(),
        readonly_end: 16, limit: 1024 * 1024, peak: 8192, auxiliary_bytes: 0 }
}
fn program(op: Op) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![],
        functions: vec![Function { name: "descriptor-control".into(), frame_size: 16, frame_align: 16,
            registers: 6, args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![op, Op::Return] }] }
}
fn open_op() -> Op { Op::DescriptorOpen { dst: 0, path: 1, flags: 2, mode: Some(3), errno: 4 } }

#[test]
fn disabled_and_partial_programs_reject_before_guest_instructions() {
    let mut p = program(open_op());
    p.functions[0].code.insert(0, Op::Trap { message: "guest ran".into() });
    assert_eq!(execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap_err(),
        "guest descriptor I/O is disabled");
    p.version |= crate::PARTIAL_VALIDATION;
    let limits = Limits { guest_descriptor_io: true, ..Limits::default() };
    assert_eq!(execute_with_engine(&p, &[], limits, Engine::Interpreter).unwrap_err(),
        "guest descriptor I/O requires complete validation");
}

#[test]
fn descriptor_encoding_registers_target_and_legacy_discriminants_are_checked() {
    use bincode::Options;
    let options = || bincode::DefaultOptions::new().with_fixint_encoding().reject_trailing_bytes();
    let old = Op::Imm { dst: 3, value: 7 };
    let bytes = options().serialize(&old).unwrap();
    let mut expected = vec![0, 0, 0, 0, 3, 0, 0, 0];
    expected.extend_from_slice(&7u128.to_le_bytes());
    assert_eq!(bytes, expected);
    assert_eq!(&options().serialize(&Op::EnvironmentGet { dst: 3, name: 4 }).unwrap()[..4], &33u32.to_le_bytes());
    assert_eq!(&options().serialize(&open_op()).unwrap()[..4], &34u32.to_le_bytes());
    for op in [open_op(), Op::DescriptorOpen { dst: 0, path: 1, flags: 2, mode: None, errno: 4 },
        Op::DescriptorWrite { dst: 0, descriptor: 1, address: 2, size: 3, errno: 4 },
        Op::DescriptorClose { dst: 0, descriptor: 1, errno: 4 },
        Op::DescriptorGetFd { dst: 0, descriptor: 1, errno: 4 }] {
        let encoded = options().serialize(&op).unwrap();
        let decoded: Op = options().deserialize(&encoded).unwrap();
        assert_eq!(format!("{decoded:?}"), format!("{op:?}"));
        let mut p = program(op);
        crate::validate(&p).unwrap();
        p.functions[0].registers = 4;
        assert_eq!(crate::validate(&p).unwrap_err(), "invalid register");
        p.functions[0].registers = 6;
        p.target = "x86_64-unknown-linux-gnu".into();
        assert!(crate::validate(&p).unwrap_err().contains("Darwin guest contract"));
    }
}

#[cfg(all(target_os = "macos", target_arch = "aarch64"))]
mod darwin {
    use super::*;
    use std::ffi::{CStr, CString, c_void};
    use std::os::unix::ffi::OsStrExt;
    use std::sync::atomic::{AtomicU64, Ordering};
    unsafe extern "C" {
        fn open(path: *const std::ffi::c_char, flags: i32, ...) -> i32;
        fn write(fd: i32, bytes: *const c_void, size: usize) -> isize;
        fn close(fd: i32) -> i32;
        fn fcntl(fd: i32, command: i32, ...) -> i32;
        fn __error() -> *mut i32;
        fn pipe(fds: *mut i32) -> i32;
        fn read(fd: i32, bytes: *mut c_void, size: usize) -> isize;
    }
    static NEXT: AtomicU64 = AtomicU64::new(0);
    struct Directory(std::path::PathBuf);
    impl Directory {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!("rust-interp-descriptor-{}-{}",
                std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
            std::fs::create_dir(&path).unwrap();
            Self(path)
        }
        fn path(&self, name: &str) -> CString { CString::new(self.0.join(name).as_os_str().as_bytes()).unwrap() }
    }
    impl Drop for Directory { fn drop(&mut self) { std::fs::remove_dir_all(&self.0).unwrap(); } }
    fn state() -> State {
        State::new(&program(open_op()), &Limits { guest_descriptor_io: true, ..Limits::default() }).unwrap().unwrap()
    }
    fn path(m: &mut Memory, name: &CStr) {
        m.bytes[32..32 + name.to_bytes_with_nul().len()].copy_from_slice(name.to_bytes_with_nul());
    }
    fn errno(m: &Memory) -> i32 { m.load(16, 4).unwrap() as u32 as i32 }
    fn native<T>(call: impl FnOnce() -> T) -> (T, i32) {
        unsafe { *__error() = 71; }
        let result = call();
        (result, unsafe { *__error() })
    }

    #[test]
    fn native_create_truncate_append_binary_empty_errno_and_getfd_agree() {
        let directory = Directory::new();
        let native_path = directory.path("native.bin");
        let guest_path = directory.path("guest.bin");
        let mut m = memory(); let mut s = state(); path(&mut m, &guest_path);
        let data = [0, 255, 17, 0, 128, 42]; m.bytes[4096..4102].copy_from_slice(&data);
        for flags in [1 | 0x200 | 0x800 | 0x1000000, 1 | 0x8, 1 | 0x400] {
            let (n, ne) = native(|| unsafe { open(native_path.as_ptr(), flags, 0o640i32) });
            assert!(n >= 0);
            m.store(16, 4, 71).unwrap(); let g = s.open(&mut m, 32, flags as u128, Some(0o640), 16).unwrap();
            assert_eq!(g, FIRST_FD as u128); assert_eq!(errno(&m), ne);
            let (nflags, ne) = native(|| unsafe { fcntl(n, 1) });
            m.store(16, 4, 71).unwrap(); assert_eq!(s.get_fd(&mut m, g, 16).unwrap(), nflags as u32 as u128);
            assert_eq!(errno(&m), ne);
            for count in [data.len(), 0] {
                let (written, ne) = native(|| unsafe { write(n, data.as_ptr().cast(), count) });
                m.store(16, 4, 71).unwrap();
                assert_eq!(s.write(&mut m, g, if count == 0 { 0 } else { 4096 }, count as u128, 16).unwrap(), written as u64 as u128);
                assert_eq!(errno(&m), ne);
            }
            let (closed, ne) = native(|| unsafe { close(n) });
            m.store(16, 4, 71).unwrap(); assert_eq!(s.close(&mut m, g, 16).unwrap(), closed as u32 as u128);
            assert_eq!(errno(&m), ne);
            assert_eq!(std::fs::read(directory.0.join("native.bin")).unwrap(), std::fs::read(directory.0.join("guest.bin")).unwrap());
        }
        let host_errno = unsafe { *__error() };
        m.store(16, 4, 19).unwrap(); let g = s.open(&mut m, 32, 0, None, 16).unwrap();
        assert_eq!(unsafe { *__error() }, host_errno);
        let (n, _) = native(|| unsafe { open(native_path.as_ptr(), 0) });
        let (written, ne) = native(|| unsafe { write(n, data.as_ptr().cast(), 1) });
        m.store(16, 4, 71).unwrap(); assert_eq!(s.write(&mut m, g, 4096, 1, 16).unwrap(), written as u64 as u128);
        assert_eq!(errno(&m), ne);
        unsafe { close(n); } s.close(&mut m, g, 16).unwrap();
        let (bad, ne) = native(|| unsafe { close(-1) });
        assert_eq!(s.close(&mut m, g, 16).unwrap(), bad as u32 as u128); assert_eq!(errno(&m), ne);
        path(&mut m, &directory.path("absent"));
        let (bad, ne) = native(|| unsafe { open(directory.path("absent").as_ptr(), 0) });
        m.store(16, 4, 71).unwrap(); assert_eq!(s.open(&mut m, 32, 0, None, 16).unwrap(), bad as u32 as u128);
        assert_eq!(errno(&m), ne);
    }

    #[test]
    fn invalid_guest_memory_precedes_file_or_close_effects_and_drop_closes_owned_fds() {
        let directory = Directory::new(); let filename = directory.path("unchanged.bin");
        std::fs::write(directory.0.join("unchanged.bin"), b"unchanged").unwrap();
        let mut m = memory(); let mut s = state(); path(&mut m, &filename);
        for error in [0, 8, 8190, 1u128 << 64] {
            assert!(s.open(&mut m, 32, 1 | 0x400, Some(0o600), error).is_err());
            assert_eq!(std::fs::read(directory.0.join("unchanged.bin")).unwrap(), b"unchanged");
        }
        for address in [0, 8192, 1u128 << 64] { assert!(s.open(&mut m, address, 1, None, 16).is_err()); }
        m.bytes[32..].fill(b'x'); assert!(s.open(&mut m, 32, 1, None, 16).is_err()); path(&mut m, &filename);
        let g = s.open(&mut m, 32, 1 | 0x8, None, 16).unwrap(); let host = s.host_fd(g as i32).unwrap();
        for (address, size) in [(0, 1), (8191, 2), (1u128 << 64, 0), (32, 1u128 << 64)] {
            assert!(s.write(&mut m, g, address, size, 16).is_err());
            assert_eq!(std::fs::read(directory.0.join("unchanged.bin")).unwrap(), b"unchanged");
        }
        assert!(s.close(&mut m, g, 0).is_err()); assert!(unsafe { fcntl(host, 1) } >= 0);
        drop(s); assert_eq!(unsafe { fcntl(host, 1) }, -1); assert_eq!(unsafe { *__error() }, 9);
    }

    #[test]
    fn guest_table_never_dispatches_unowned_host_numbers_and_resource_limit_is_a_trap() {
        let directory = Directory::new(); let filename = directory.path("file.bin");
        let mut m = memory(); let mut s = state(); path(&mut m, &filename);
        let n = unsafe { open(filename.as_ptr(), 1 | 0x200, 0o600i32) }; assert!(n >= 0);
        for g in [0, 1, 2, u32::MAX as u128, 9999, n as u128] {
            assert_eq!(s.get_fd(&mut m, g, 16).unwrap(), u32::MAX as u128);
            assert_eq!(s.close(&mut m, g, 16).unwrap(), u32::MAX as u128);
            assert_eq!(s.write(&mut m, g, 0, 0, 16).unwrap(), u64::MAX as u128);
        }
        assert!(unsafe { fcntl(n, 1) } >= 0); unsafe { close(n); }
        // Shorten only the test table to exercise its limit without consuming
        // the host's descriptor limit or any unrelated process resources.
        s.fds.truncate(1); let g = s.open(&mut m, 32, 1, None, 16).unwrap();
        m.store(16, 4, 71).unwrap();
        assert_eq!(s.open(&mut m, 32, 1 | 0x400, None, 16).unwrap_err(), "guest descriptor limit exceeded");
        assert_eq!(errno(&m), 71); s.close(&mut m, g, 16).unwrap();
        assert_eq!(s.open(&mut m, 32, 1, None, 16).unwrap(), g);
    }

    #[test]
    fn nonblocking_owned_pipe_exposes_short_write_and_eagain_without_retry() {
        let mut pipe_fds = [-1; 2]; assert_eq!(unsafe { pipe(pipe_fds.as_mut_ptr()) }, 0);
        assert_eq!(unsafe { fcntl(pipe_fds[1], 4, 4i32) }, 0); // F_SETFL/O_NONBLOCK: test setup only.
        let mut s = state(); s.fds[0] = Some(pipe_fds[1]); s.fds[1] = Some(pipe_fds[0]);
        let mut native_fds = [-1; 2]; assert_eq!(unsafe { pipe(native_fds.as_mut_ptr()) }, 0);
        assert_eq!(unsafe { fcntl(native_fds[1], 4, 4i32) }, 0);
        let mut native_owner = state(); native_owner.fds[0] = Some(native_fds[1]); native_owner.fds[1] = Some(native_fds[0]);
        let mut m = memory(); m.bytes.resize(2 * 1024 * 1024, 0x5a); m.limit = 4 * 1024 * 1024;
        m.store(16, 4, 71).unwrap();
        let size = (m.bytes.len() - 32) as u128;
        let (native_written, _) = native(|| unsafe { write(native_fds[1], m.bytes[32..].as_ptr().cast(), size as usize) });
        assert!(native_written > 0 && (native_written as u128) < size);
        let (native_again, native_error) = native(|| unsafe { write(native_fds[1], m.bytes[32..].as_ptr().cast(), size as usize) });
        assert_eq!(native_again, -1);
        let written = s.write(&mut m, 3, 32, size, 16).unwrap();
        assert!(written > 0 && written < size);
        let again = s.write(&mut m, 3, 32, size, 16).unwrap();
        assert_eq!(again, native_again as u64 as u128); assert_eq!(errno(&m), native_error);
        let mut bytes = vec![0; written as usize]; let got = unsafe { read(pipe_fds[0], bytes.as_mut_ptr().cast(), bytes.len()) };
        assert_eq!(got as u128, written); assert_eq!(bytes, m.bytes[32..32 + written as usize]);
        let mut bytes = vec![0; native_written as usize];
        assert_eq!(unsafe { read(native_fds[0], bytes.as_mut_ptr().cast(), bytes.len()) }, native_written);
        assert_eq!(bytes, m.bytes[32..32 + native_written as usize]);
        s.close(&mut m, 3, 16).unwrap();
    }
}
