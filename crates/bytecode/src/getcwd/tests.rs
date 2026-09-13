use super::*;
use crate::{Engine, Function, Op, Slot, VERSION, execute_with_engine};

fn program() -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![],
        functions: vec![Function { name: "getcwd-control".into(), frame_size: 16, frame_align: 16,
            registers: 4, args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![
                Op::Trap { message: "guest executed".into() },
                Op::CurrentDirectory { dst: 0, address: 1, size: 2, errno: 3 }, Op::Return] }] }
}

#[test]
fn disabled_partial_target_and_register_admission_precede_both_engines() {
    for engine in [Engine::Interpreter, Engine::Jit] {
        let p = program();
        assert_eq!(execute_with_engine(&p, &[], Limits::default(), engine).unwrap_err(), "guest getcwd is disabled");
        let mut partial = p.clone(); partial.version |= crate::PARTIAL_VALIDATION;
        assert_eq!(execute_with_engine(&partial, &[], Limits { guest_getcwd: true, ..Limits::default() }, engine).unwrap_err(),
            "guest getcwd requires complete validation");
    }
    let mut p = program(); p.target = "x86_64-unknown-linux-gnu".into();
    assert_eq!(crate::validate(&p).unwrap_err(), "getcwd requires the Darwin guest contract");
    let mut p = program(); p.functions[0].registers = 3;
    assert_eq!(crate::validate(&p).unwrap_err(), "invalid register");
    use bincode::Options;
    let options = || bincode::DefaultOptions::new().with_fixint_encoding().reject_trailing_bytes();
    let old = Op::DescriptorGetFd { dst: 0, descriptor: 1, errno: 2 };
    assert_eq!(&options().serialize(&old).unwrap()[..4], &37u32.to_le_bytes());
    let op = program().functions[0].code[1].clone();
    let bytes = options().serialize(&op).unwrap();
    assert_eq!(&bytes[..4], &38u32.to_le_bytes());
    let decoded: Op = options().deserialize(&bytes).unwrap();
    assert_eq!(format!("{decoded:?}"), format!("{op:?}"));
}

#[cfg(all(target_os = "macos", target_arch = "aarch64"))]
mod darwin {
    use super::*;
    use std::ffi::{CStr, c_char, c_void};
    unsafe extern "C" {
        fn getcwd(buffer: *mut c_char, size: usize) -> *mut c_char;
        fn free(pointer: *mut c_void);
        fn __error() -> *mut i32;
    }
    fn memory(allocations: usize) -> Memory {
        Memory { bytes: vec![0xa5; 8192].into(), heap: crate::heap::Heap::with_statics(&[0; 32], allocations),
            readonly_end: 16, limit: 1024 * 1024, peak: 8224, auxiliary_bytes: 0 }
    }
    fn native<T>(call: impl FnOnce() -> T) -> (T, i32) {
        unsafe {
            let saved = *__error(); *__error() = 71;
            let result = call(); let after = *__error(); *__error() = saved;
            (result, after)
        }
    }

    #[test]
    fn native_buffer_null_sizes_full_bytes_errno_and_owned_free_agree() {
        let mut m = memory(4);
        let (p, _) = native(|| unsafe { getcwd(std::ptr::null_mut(), 0) });
        assert!(!p.is_null());
        let expected = unsafe { CStr::from_ptr(p) }.to_bytes_with_nul().to_vec();
        unsafe { free(p.cast()); }
        assert!(expected.len() < 4096);
        for size in [0, 1, expected.len() - 1, expected.len(), 4096] {
            let mut buffer = vec![0xa5; 4096];
            let (p, after) = native(|| unsafe { getcwd(buffer.as_mut_ptr().cast(), size) });
            let host_errno = unsafe { *__error() };
            m.bytes[32..4128].fill(0xa5); m.store(16, 4, 71).unwrap();
            assert_eq!(m.getcwd(32, size as u128, 16, 0).unwrap(), if p.is_null() { 0 } else { 32 });
            assert_eq!(m.read(32, 4096).unwrap(), buffer);
            assert_eq!(m.load(16, 4).unwrap(), after as u32 as u128);
            assert_eq!(unsafe { *__error() }, host_errno);
        }
        for size in [0, 1, 4096, usize::MAX] {
            let (p, after) = native(|| unsafe { getcwd(std::ptr::null_mut(), size) });
            assert!(!p.is_null());
            let native_bytes = unsafe { CStr::from_ptr(p) }.to_bytes_with_nul().to_vec();
            unsafe { free(p.cast()); }
            let host_errno = unsafe { *__error() };
            m.store(16, 4, 71).unwrap();
            let guest = m.getcwd(0, size as u128, 16, 0).unwrap();
            assert_ne!(guest, 0); assert_ne!(guest, p as usize as u128);
            assert_eq!(m.read(guest as usize, expected.len()).unwrap(), native_bytes);
            assert_eq!(m.load(16, 4).unwrap(), after as u32 as u128);
            assert_eq!(unsafe { *__error() }, host_errno);
            let grown = m.c_reallocate(guest, (expected.len() + 17) as u128, 16, 0).unwrap();
            assert_ne!(grown, 0); assert_eq!(m.read(grown as usize, expected.len()).unwrap(), expected);
            m.c_deallocate(grown).unwrap(); assert_eq!(m.heap.bytes, vec![0; 32]);
        }
    }

    #[test]
    fn invalid_pointer_size_and_errno_fail_before_memory_or_host_errno_changes() {
        let mut m = memory(4); m.store(16, 4, 71).unwrap();
        let bytes = m.bytes.to_vec(); let heap = m.heap.bytes.clone();
        for (address, size, error) in [(8, 8, 16), (8191, 2, 16), (32, usize::MAX as u128, 16),
            (1u128 << 64, 0, 16), (0, 1u128 << 64, 16), (0, 0, 0), (0, 0, 8), (0, 0, 8190), (0, 0, 1u128 << 64)] {
            let host_errno = unsafe { *__error() };
            assert!(m.getcwd(address, size, error, 0).is_err());
            assert_eq!(m.bytes.as_ref(), bytes.as_slice()); assert_eq!(m.heap.bytes, heap);
            assert_eq!(unsafe { *__error() }, host_errno);
        }
    }

    #[test]
    fn null_allocation_charges_live_count_register_and_byte_budgets_without_leaks() {
        for no_count in [true, false] {
            let mut m = memory(if no_count { 0 } else { 4 });
            if !no_count { m.limit = m.total_len() + 32; }
            m.store(16, 4, 71).unwrap(); let heap = m.heap.bytes.clone();
            let host_errno = unsafe { *__error() };
            assert_eq!(m.getcwd(0, usize::MAX as u128, 16, 32).unwrap(), 0);
            assert_eq!(m.load(16, 4).unwrap(), 12);
            assert_eq!(m.heap.bytes, heap); assert_eq!(unsafe { *__error() }, host_errno);
            m.heap = crate::heap::Heap::with_statics(&[0; 32], 1); m.limit = 1024 * 1024;
            let p = m.getcwd(0, 0, 16, 0).unwrap(); assert_ne!(p, 0);
            assert_eq!(m.getcwd(0, 0, 16, 0).unwrap(), 0);
            m.c_deallocate(p).unwrap(); assert_eq!(m.heap.bytes, vec![0; 32]);
            let p = m.getcwd(0, 0, 16, 0).unwrap(); assert_ne!(p, 0); m.c_deallocate(p).unwrap();
        }
    }
}
