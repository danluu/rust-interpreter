use super::*;
use crate::{Engine, Function, Slot, VERSION, execute_with_engine};

fn stat_op() -> Op { Op::DescriptorStat { dst: 0, descriptor: 1, address: 2, errno: 3 } }
fn program() -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![],
        functions: vec![Function { name: "stat-admission".into(), frame_size: 16, frame_align: 8,
            registers: 4, args: vec![], result: Slot { offset: 0, size: 0 },
            code: vec![Op::Trap { message: "guest ran".into() }, stat_op(), Op::Return] }] }
}

#[test]
fn stat_encoding_all_registers_and_capability_preflight_cover_both_engines() {
    use bincode::Options;
    let options = bincode::DefaultOptions::new().with_fixint_encoding().reject_trailing_bytes();
    let bytes = options.serialize(&stat_op()).unwrap();
    assert_eq!(&bytes[..4], &39u32.to_le_bytes());
    let decoded: Op = options.deserialize(&bytes).unwrap();
    assert_eq!(format!("{decoded:?}"), format!("{:?}", stat_op()));
    assert_eq!(&options.serialize(&Op::CurrentDirectory { dst: 0, address: 1, size: 2, errno: 3 }).unwrap()[..4], &38u32.to_le_bytes());
    for bad in [Op::DescriptorStat { dst: 4, descriptor: 1, address: 2, errno: 3 },
        Op::DescriptorStat { dst: 0, descriptor: 4, address: 2, errno: 3 },
        Op::DescriptorStat { dst: 0, descriptor: 1, address: 4, errno: 3 },
        Op::DescriptorStat { dst: 0, descriptor: 1, address: 2, errno: 4 }] {
        let mut p = program(); p.functions[0].code[1] = bad;
        assert_eq!(crate::validate(&p).unwrap_err(), "invalid register");
    }
    for engine in [Engine::Interpreter, Engine::Jit] {
        let p = program();
        assert_eq!(execute_with_engine(&p, &[], Limits::default(), engine).unwrap_err(), "guest descriptor I/O is disabled");
        let mut p = p; p.version |= crate::PARTIAL_VALIDATION;
        assert_eq!(execute_with_engine(&p, &[], Limits { guest_descriptor_io: true, ..Limits::default() }, engine).unwrap_err(),
            "guest descriptor I/O requires complete validation");
    }
    let mut p = program(); p.target = "x86_64-unknown-linux-gnu".into();
    assert!(crate::validate(&p).unwrap_err().contains("Darwin guest contract"));
}

#[cfg(all(target_os = "macos", target_arch = "aarch64"))]
mod darwin {
    use super::*;
    use std::os::fd::AsRawFd;
    use std::os::unix::fs::MetadataExt;
    use std::sync::atomic::{AtomicU64, Ordering};
    unsafe extern "C" { fn fstat(fd: i32, output: *mut StatBuffer) -> i32; fn __error() -> *mut i32; }
    static NEXT: AtomicU64 = AtomicU64::new(0);
    struct File(std::path::PathBuf);
    impl File {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!("rust-interp-stat-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
            std::fs::OpenOptions::new().write(true).create_new(true).open(&path).unwrap();
            Self(path)
        }
    }
    impl Drop for File { fn drop(&mut self) { std::fs::remove_file(&self.0).unwrap(); } }
    fn memory() -> Memory {
        Memory { bytes: vec![0xa5; 512].into(), heap: crate::heap::Heap::default(),
            readonly_end: 16, limit: 1024 * 1024, peak: 512, auxiliary_bytes: 0 }
    }
    fn state() -> State { State::new(&program(), &Limits { guest_descriptor_io: true, ..Limits::default() }).unwrap().unwrap() }
    fn number(bytes: &[u8], offset: usize, size: usize) -> u64 {
        let mut value = [0; 8]; value[..size].copy_from_slice(&bytes[offset..offset + size]); u64::from_le_bytes(value)
    }
    #[test]
    fn stat_full_native_bytes_named_metadata_size_changes_and_errno_agree() {
        use std::os::fd::IntoRawFd;
        let file = File::new(); let native = std::fs::File::open(&file.0).unwrap();
        let mut s = state(); s.fds[0] = Some(std::fs::File::open(&file.0).unwrap().into_raw_fd());
        let mut m = memory();
        for contents in [b"abc".as_slice(), b"longer\0contents\xff".as_slice()] {
            std::fs::write(&file.0, contents).unwrap();
            let mut expected = StatBuffer([0xa5; STAT_BYTES]);
            unsafe { *__error() = 71; }
            let result = unsafe { fstat(native.as_raw_fd(), &mut expected) };
            let error = unsafe { *__error() }; assert_eq!(result, 0);
            m.bytes[32..32 + STAT_BYTES].fill(0xa5); m.store(16, 4, 71).unwrap();
            unsafe { *__error() = 93; }
            assert_eq!(s.stat(&mut m, 3, 32, 16).unwrap(), result as u32 as u128);
            assert_eq!(unsafe { *__error() }, 93);
            assert_eq!(m.load(16, 4).unwrap(), error as u32 as u128);
            assert_eq!(m.read(32, STAT_BYTES).unwrap(), &expected.0);
            let meta = native.metadata().unwrap();
            assert_eq!(number(&expected.0, 0, 4), meta.dev() as u32 as u64);
            assert_eq!(number(&expected.0, 4, 2), meta.mode() as u64);
            assert_eq!(number(&expected.0, 6, 2), meta.nlink() as u16 as u64);
            assert_eq!(number(&expected.0, 8, 8), meta.ino());
            assert_eq!(number(&expected.0, 96, 8), contents.len() as u64);
            assert_eq!(number(&expected.0, 104, 8), meta.blocks());
            assert_eq!(number(&expected.0, 112, 4), meta.blksize());
        }
    }
    #[test]
    fn stat_invalid_memory_and_unmapped_or_closed_descriptors_preserve_output() {
        let file = File::new(); let native = std::fs::File::open(&file.0).unwrap();
        let mut s = state(); let mut m = memory();
        for (address, error) in [(0,16),(8,16),(400,16),(1u128<<64,16),(32,0),(32,8),(32,510),(32,1u128<<64)] {
            let before = m.bytes.to_vec(); unsafe { *__error() = 93; }
            assert!(s.stat(&mut m, native.as_raw_fd() as u128, address, error).is_err());
            assert_eq!(&*m.bytes, before.as_slice()); assert_eq!(unsafe { *__error() }, 93);
        }
        for descriptor in [0, 1, 2, u32::MAX as u128, 9999, native.as_raw_fd() as u128] {
            m.bytes[32..32 + STAT_BYTES].fill(0xa5); m.store(16, 4, 71).unwrap();
            unsafe { *__error() = 93; }
            assert_eq!(s.stat(&mut m, descriptor, 32, 16).unwrap(), u32::MAX as u128);
            assert_eq!(m.load(16, 4).unwrap(), 9); assert_eq!(m.read(32, STAT_BYTES).unwrap(), &[0xa5; STAT_BYTES]);
            assert_eq!(unsafe { *__error() }, 93);
        }
        assert!(s.stat(&mut m, 1u128 << 32, 32, 16).is_err());
        use std::os::fd::IntoRawFd;
        s.fds[0] = Some(std::fs::File::open(&file.0).unwrap().into_raw_fd());
        s.close(&mut m, 3, 16).unwrap();
        m.bytes[32..32 + STAT_BYTES].fill(0xa5);
        assert_eq!(s.stat(&mut m, 3, 32, 16).unwrap(), u32::MAX as u128);
        assert_eq!(m.read(32, STAT_BYTES).unwrap(), &[0xa5; STAT_BYTES]);
        assert!(native.metadata().is_ok()); // The unowned host descriptor remains usable.
    }
}
