//! Owned MAP_JIT publisher and ABI probes, copied from the qualified custom JIT.
use super::{Cursor, MAX_CODE_BYTES};
#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
pub(super) mod memory {
    use std::ffi::c_void;

    #[cfg(test)]
    std::arch::global_asm!(r#"
        .text
        .p2align 2
        .globl _rust_interp_scalar_abi_probe
    _rust_interp_scalar_abi_probe:
        stp x19, x20, [sp, #-32]!
        stp x29, x30, [sp, #16]
        mov x29, sp
        mov x20, x2
        mov x16, x0
        mov x17, x1
        mov x19, #0x1357
        ldp x0, x1, [x17]
        ldp x2, x3, [x17, #16]
        ldp x4, x5, [x17, #32]
        ldp x6, x7, [x17, #48]
        blr x16
        str x0, [x20]
        str x19, [x20, #8]
        mov x9, sp
        str x9, [x20, #16]
        str x29, [x20, #24]
        ldp x29, x30, [sp, #16]
        ldp x19, x20, [sp], #32
        ret
        .p2align 2
        .globl _rust_interp_scalar_preservation_probe
    _rust_interp_scalar_preservation_probe:
        stp x19, x20, [sp, #-112]!
        stp x21, x22, [sp, #16]
        stp x23, x24, [sp, #32]
        stp x25, x26, [sp, #48]
        stp x27, x28, [sp, #64]
        stp x29, x30, [sp, #80]
        str x2, [sp, #96]
        mov x29, sp
        mov x16, x0
        mov x17, x1
        mov x19, #0x1357
        mov x20, #0x2468
        mov x21, #0x3579
        mov x22, #0x468a
        mov x23, #0x579b
        mov x24, #0x68ac
        mov x25, #0x79bd
        mov x26, #0x8ace
        mov x27, #0x9bdf
        mov x28, #0xace0
        ldp x0, x1, [x17]
        ldp x2, x3, [x17, #16]
        ldp x4, x5, [x17, #32]
        ldp x6, x7, [x17, #48]
        blr x16
        ldr x10, [sp, #96]
        stp x0, x19, [x10]
        stp x20, x21, [x10, #16]
        stp x22, x29, [x10, #32]
        mov x9, sp
        str x9, [x10, #48]
        stp x23, x24, [x10, #56]
        stp x25, x26, [x10, #72]
        stp x27, x28, [x10, #88]
        ldp x19, x20, [sp]
        ldp x21, x22, [sp, #16]
        ldp x23, x24, [sp, #32]
        ldp x25, x26, [sp, #48]
        ldp x27, x28, [sp, #64]
        ldp x29, x30, [sp, #80]
        add sp, sp, #112
        ret
    "#);

    #[cfg(test)]
    unsafe extern "C" {
        fn rust_interp_scalar_abi_probe(entry: *mut c_void, arguments: *const usize, output: *mut usize);
        fn rust_interp_scalar_preservation_probe(entry: *mut c_void, arguments: *const usize, output: *mut usize);
    }

    unsafe extern "C" {
        fn mmap(
            addr: *mut c_void,
            len: usize,
            prot: i32,
            flags: i32,
            fd: i32,
            off: i64,
        ) -> *mut c_void;
        fn munmap(addr: *mut c_void, len: usize) -> i32;
        fn pthread_jit_write_protect_np(enabled: i32);
        fn sys_icache_invalidate(start: *mut c_void, len: usize);
    }

    pub struct Code {
        ptr: *mut c_void,
        len: usize,
        used: usize,
    }
    impl Code {
        pub fn published(&self) -> (usize, &[u8]) {
            // SAFETY: append initializes exactly [ptr, ptr+used), used <= len.
            // The mapping is readable in execution mode, remains owned by
            // self, and cannot be unmapped or appended through this borrow.
            (self.ptr as usize, unsafe { std::slice::from_raw_parts(self.ptr.cast(), self.used) })
        }
        #[cfg(test)]
        pub unsafe fn tree_abi_probe(&self, offset: usize, arguments: [usize;8]) -> [usize;13] {
            assert!(offset < self.used);
            let mut output = [0;13];
            // Same exclusive storage contract as call(); the wrapper verifies
            // x19–x28 plus SP/LR, including persistent register pairs.
            unsafe {
                rust_interp_scalar_preservation_probe(self.ptr.cast::<u8>().add(offset).cast(), arguments.as_ptr(), output.as_mut_ptr());
            }
            output
        }
        #[cfg(test)]
        pub unsafe fn abi_probe(&self, offset: usize, arguments: [usize;8]) -> [usize;4] {
            assert!(offset < self.used);
            let mut output = [0;4];
            // Test callers supply the same live storage and cursor as call().
            // The assembly wrapper checks the native callee's x19 and SP.
            unsafe {
                rust_interp_scalar_abi_probe(self.ptr.cast::<u8>().add(offset).cast(), arguments.as_ptr(), output.as_mut_ptr());
            }
            output
        }
        pub fn reserve(len: usize) -> Result<Self, String> {
            if len == 0 || len > super::MAX_CODE_BYTES {
                return Err("JIT code size outside supported range".into());
            }
            // One bounded MAP_JIT arena. Appending never moves older entries.
            // This VM is single-threaded; no guest code is running during writes.
            let ptr = unsafe { mmap(std::ptr::null_mut(), len, 7, 0x1802, -1, 0) };
            if ptr as isize == -1 {
                return Err(format!("allocate JIT code: {}", std::io::Error::last_os_error()));
            }
            Ok(Self { ptr, len, used: 0 })
        }
        pub fn append(&mut self, words: &[u32]) -> Result<usize, String> {
            let bytes = words.len().checked_mul(4).ok_or("JIT code size overflow")?;
            let end = self.used.checked_add(bytes).filter(|end| *end <= self.len)
                .ok_or("JIT arena capacity exceeded")?;
            let offset = self.used;
            if bytes != 0 {
                // All fallible work is complete before write protection changes.
                // Only immutable new words are copied; committed code is untouched.
                unsafe {
                    let destination = self.ptr.cast::<u8>().add(offset);
                    pthread_jit_write_protect_np(0);
                    std::ptr::copy_nonoverlapping(words.as_ptr().cast::<u8>(), destination, bytes);
                    pthread_jit_write_protect_np(1);
                    sys_icache_invalidate(destination.cast(), bytes);
                }
            }
            self.used = end;
            Ok(offset)
        }
        pub unsafe fn call(
            &self,
            offset: usize,
            registers: *mut u128,
            base: usize,
            memory: *mut u8,
            len: usize,
            readonly: usize,
            heap: *mut u8,
            heap_len: usize,
            cursor: *mut super::Cursor,
        ) -> u64 {
            type Entry = unsafe extern "C" fn(
                *mut u128,
                usize,
                *mut u8,
                usize,
                usize,
                *mut u8,
                usize,
                *mut super::Cursor,
            ) -> u64;
            // Only offsets generated by this emitter reach here. The mapping
            // lives through the call and all storage pointers cover the
            // validated machine's current allocations.
            let function: Entry = unsafe { std::mem::transmute(self.ptr.cast::<u8>().add(offset)) };
            unsafe { function(registers, base, memory, len, readonly, heap, heap_len, cursor) }
        }
    }
    impl Drop for Code {
        fn drop(&mut self) {
            unsafe {
                munmap(self.ptr, self.len);
            }
        }
    }
}
