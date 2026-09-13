//! Opt-in Darwin getcwd. Native allocations remain private to the adapter.
use crate::{Limits, Memory, Program};

pub(super) fn admit(program: &Program, limits: &Limits) -> Result<(), String> {
    if !limits.guest_getcwd { return Err("guest getcwd is disabled".into()); }
    if program.version & crate::PARTIAL_VALIDATION != 0 {
        return Err("guest getcwd requires complete validation".into());
    }
    if program.target != "aarch64-apple-darwin"
        || !cfg!(all(target_os = "macos", target_arch = "aarch64")) {
        return Err("guest getcwd requires AArch64 Darwin guest and host".into());
    }
    Ok(())
}

impl Memory {
    pub(super) fn getcwd(&mut self, address: u128, size: u128, errno: u128,
        registers: usize) -> Result<u128, String> {
        let address = usize::try_from(address).map_err(|_| "getcwd pointer exceeds guest width")?;
        let size = usize::try_from(size).map_err(|_| "getcwd size exceeds guest width")?;
        let error = self.c_output(errno, 4)?;
        let prior = self.load(error, 4)? as u32 as i32;
        if address == 0 {
            // Darwin ignores size for NULL, including nonzero/maximum sizes.
            // Capture libc's actual path and errno before guest allocation;
            // its private allocation is freed on every closure return path.
            return host::allocated(prior, |path, after| {
                let Some(path) = path else {
                    self.store(error, 4, after as u32 as u128)?;
                    return Ok(0);
                };
                let pointer = self.c_allocate(1, path.len() as u128, errno, false, registers)?;
                if pointer == 0 { return Ok(0); } // Existing allocator wrote ENOMEM.
                let (heap, range) = self.range(pointer as usize, path.len())?;
                debug_assert!(heap);
                self.heap.bytes[range].copy_from_slice(path);
                self.store(error, 4, after as u32 as u128)?;
                Ok(pointer)
            });
        }
        // A non-NULL zero-size call never accesses the supplied buffer and
        // returns native EINVAL. Otherwise check the complete writable span
        // before exposing a host slice. No guest integer becomes a host pointer.
        if size != 0 { self.c_output(address as u128, size)?; }
        let (heap, range) = self.range(address, size)?;
        let bytes = if heap { &mut self.heap.bytes[range] } else { &mut self.bytes[range] };
        let (success, after) = host::buffer(bytes, prior)?;
        self.store(error, 4, after as u32 as u128)?;
        Ok(if success { address as u128 } else { 0 })
    }
}

#[cfg(all(target_os = "macos", target_arch = "aarch64"))]
mod host {
    use std::ffi::{CStr, c_char, c_void};
    unsafe extern "C" {
        #[link_name = "getcwd"] fn c_getcwd(buffer: *mut c_char, size: usize) -> *mut c_char;
        #[link_name = "free"] fn c_free(pointer: *mut c_void);
        fn __error() -> *mut i32;
    }
    struct Errno(i32);
    impl Errno {
        fn seed(prior: i32) -> Self {
            unsafe { let saved = *__error(); *__error() = prior; Self(saved) }
        }
    }
    impl Drop for Errno { fn drop(&mut self) { unsafe { *__error() = self.0; } } }
    struct Allocation(*mut c_char);
    impl Drop for Allocation { fn drop(&mut self) { unsafe { c_free(self.0.cast()); } } }

    pub(super) fn buffer(bytes: &mut [u8], prior: i32) -> Result<(bool, i32), String> {
        let _restore = Errno::seed(prior);
        let pointer = bytes.as_mut_ptr().cast();
        let result = unsafe { c_getcwd(pointer, bytes.len()) };
        let after = unsafe { *__error() };
        if !result.is_null() && result != pointer { return Err("native getcwd returned a different buffer".into()); }
        Ok((!result.is_null(), after))
    }

    pub(super) fn allocated<T>(prior: i32, use_path: impl FnOnce(Option<&[u8]>, i32) -> Result<T, String>)
        -> Result<T, String> {
        // Drop order: release the native allocation, then restore host errno.
        // Neither Rust allocation, guest ENOMEM nor free obscures native errno.
        let _restore = Errno::seed(prior);
        let result = unsafe { c_getcwd(std::ptr::null_mut(), 0) };
        let after = unsafe { *__error() };
        let owned = Allocation(result);
        let path = if owned.0.is_null() { None }
            else { Some(unsafe { CStr::from_ptr(owned.0) }.to_bytes_with_nul()) };
        use_path(path, after)
    }
}

#[cfg(not(all(target_os = "macos", target_arch = "aarch64")))]
mod host {
    pub(super) fn buffer(_: &mut [u8], _: i32) -> Result<(bool, i32), String> { Err("getcwd host unavailable".into()) }
    pub(super) fn allocated<T>(_: i32, _: impl FnOnce(Option<&[u8]>, i32) -> Result<T, String>) -> Result<T, String> {
        Err("getcwd host unavailable".into())
    }
}

#[cfg(test)]
mod tests;
