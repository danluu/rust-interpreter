//! Opt-in Darwin descriptor primitives. Only this execution's open files exist
//! in the guest namespace; VM descriptors and inherited streams are not inputs.
use crate::{Limits, Memory, Op, Program};

const FIRST_FD: i32 = 3;
const FD_COUNT: usize = 256;
const EBADF: u128 = 9;
const O_CREAT: i32 = 0x0200;
// Pinned AArch64 Darwin ABI; independently checked against SDK stat.h by the native suite.
const STAT_BYTES: usize = 144;
#[repr(C, align(8))]
struct StatBuffer([u8; STAT_BYTES]);

pub(super) fn is_descriptor_op(op: &Op) -> bool {
    matches!(op, Op::DescriptorOpen { .. } | Op::DescriptorWrite { .. }
        | Op::DescriptorClose { .. } | Op::DescriptorGetFd { .. } | Op::DescriptorStat { .. })
}

pub(super) struct State { fds: Vec<Option<i32>> }

impl State {
    pub(super) fn new(program: &Program, limits: &Limits) -> Result<Option<Self>, String> {
        if !program.functions.iter().any(|f| f.code.iter().any(is_descriptor_op)) { return Ok(None); }
        if !limits.guest_descriptor_io { return Err("guest descriptor I/O is disabled".into()); }
        if program.version & crate::PARTIAL_VALIDATION != 0 {
            return Err("guest descriptor I/O requires complete validation".into());
        }
        if program.target != "aarch64-apple-darwin"
            || !cfg!(all(target_os = "macos", target_arch = "aarch64")) {
            return Err("guest descriptor I/O requires AArch64 Darwin guest and host".into());
        }
        let bytes = FD_COUNT * std::mem::size_of::<Option<i32>>();
        if bytes > limits.memory { return Err("descriptor table exceeds guest memory limit".into()); }
        Ok(Some(Self { fds: vec![None; FD_COUNT] }))
    }

    pub(super) fn charged_bytes(&self) -> usize { self.fds.len() * std::mem::size_of::<Option<i32>>() }

    fn index(&self, descriptor: i32) -> Option<usize> {
        descriptor.checked_sub(FIRST_FD).and_then(|n| usize::try_from(n).ok())
            .filter(|&n| n < self.fds.len())
    }

    fn host_fd(&self, descriptor: i32) -> Option<i32> { self.index(descriptor).and_then(|n| self.fds[n]) }

    pub(super) fn open(&mut self, memory: &mut Memory, path: u128, flags: u128,
        mode: Option<u128>, errno: u128) -> Result<u128, String> {
        let flags = integer(flags)?;
        let mode = mode.map(integer).transpose()?;
        if flags & O_CREAT != 0 && mode.is_none() {
            return Err("guest open with O_CREAT requires its promoted mode argument".into());
        }
        let error = memory.c_output(errno, 4)?;
        let prior = memory.load(error, 4)? as u32 as i32;
        // Borrow only a fully checked, terminated host slice. No allocation,
        // guest memory mutation or descriptor-table mutation precedes this.
        let path = c_path(memory, path)?;
        let slot = self.fds.iter().position(Option::is_none)
            .ok_or("guest descriptor limit exceeded")?;
        let (fd, after) = host::open(path, flags, mode, prior)?;
        // Reserve the already allocated slot before the infallible checked
        // errno write. Host descriptor numbers (including 0/1/2) never escape.
        let result = if fd >= 0 { self.fds[slot] = Some(fd); FIRST_FD + slot as i32 } else { fd };
        memory.store(error, 4, after as u32 as u128)?;
        Ok(result as u32 as u128)
    }

    pub(super) fn write(&mut self, memory: &mut Memory, descriptor: u128,
        address: u128, size: u128, errno: u128) -> Result<u128, String> {
        let descriptor = integer(descriptor)?;
        let address = word(address)?;
        let size = word(size)?;
        let error = memory.c_output(errno, 4)?;
        let prior = memory.load(error, 4)? as u32 as i32;
        // Even zero-byte writes validate the integer width, then use the
        // existing empty-slice convention. libc sees a valid host empty slice.
        let bytes = memory.read(address, size)?;
        let Some(fd) = self.host_fd(descriptor) else {
            memory.store(error, 4, EBADF)?;
            return Ok(u64::MAX as u128);
        };
        // One syscall, not write_all: partial writes, EINTR and errors remain
        // visible to the ordinary guest std/libc caller.
        let (result, after) = host::write(fd, bytes, prior)?;
        memory.store(error, 4, after as u32 as u128)?;
        Ok(result as u64 as u128)
    }

    pub(super) fn stat(&mut self, memory: &mut Memory, descriptor: u128,
        address: u128, errno: u128) -> Result<u128, String> {
        let descriptor = integer(descriptor)?;
        let address = memory.c_output(address, STAT_BYTES)?;
        let error = memory.c_output(errno, 4)?;
        let prior = memory.load(error, 4)? as u32 as i32;
        let Some(fd) = self.host_fd(descriptor) else {
            memory.store(error, 4, EBADF)?;
            return Ok(u32::MAX as u128);
        };
        // Seed every byte, including padding. libc sees only an aligned private
        // buffer; failed calls and untouched bytes retain their native behavior.
        let mut buffer = StatBuffer([0; STAT_BYTES]);
        buffer.0.copy_from_slice(memory.read(address, STAT_BYTES)?);
        let (result, after) = host::stat(fd, &mut buffer, prior)?;
        let (heap, range) = memory.range(address, STAT_BYTES)?;
        if heap { memory.heap.bytes[range].copy_from_slice(&buffer.0); }
        else { memory.bytes[range].copy_from_slice(&buffer.0); }
        memory.store(error, 4, after as u32 as u128)?;
        Ok(result as u32 as u128)
    }

    pub(super) fn close(&mut self, memory: &mut Memory, descriptor: u128,
        errno: u128) -> Result<u128, String> {
        let descriptor = integer(descriptor)?;
        let error = memory.c_output(errno, 4)?;
        let prior = memory.load(error, 4)? as u32 as i32;
        let Some(slot) = self.index(descriptor).filter(|&n| self.fds[n].is_some()) else {
            memory.store(error, 4, EBADF)?;
            return Ok(u32::MAX as u128);
        };
        let fd = self.fds[slot].take().unwrap();
        // Darwin releases a nonguarded owned descriptor before returning
        // file-close errors. Never retry or leave a stale host number in Drop.
        let (result, after) = host::close(fd, prior)?;
        memory.store(error, 4, after as u32 as u128)?;
        Ok(result as u32 as u128)
    }

    pub(super) fn get_fd(&mut self, memory: &mut Memory, descriptor: u128,
        errno: u128) -> Result<u128, String> {
        let descriptor = integer(descriptor)?;
        let error = memory.c_output(errno, 4)?;
        let prior = memory.load(error, 4)? as u32 as i32;
        let Some(fd) = self.host_fd(descriptor) else {
            memory.store(error, 4, EBADF)?;
            return Ok(u32::MAX as u128);
        };
        let (result, after) = host::get_fd(fd, prior)?;
        memory.store(error, 4, after as u32 as u128)?;
        Ok(result as u32 as u128)
    }
}

impl Drop for State {
    fn drop(&mut self) {
        for fd in &mut self.fds {
            if let Some(fd) = fd.take() { let _ = host::close(fd, 0); }
        }
    }
}

fn integer(value: u128) -> Result<i32, String> {
    u32::try_from(value).map(|v| v as i32).map_err(|_| "descriptor operand exceeds C int width".into())
}
fn word(value: u128) -> Result<usize, String> {
    usize::try_from(value).map_err(|_| "descriptor operand exceeds guest pointer width".into())
}
fn c_path(memory: &Memory, address: u128) -> Result<&[u8], String> {
    let (heap, range) = memory.range(word(address)?, 1)?;
    let tail = if heap { &memory.heap.bytes[range.start..] } else { &memory.bytes[range.start..] };
    let end = tail.iter().position(|&byte| byte == 0).ok_or("unterminated guest path")?;
    Ok(&tail[..=end])
}

#[cfg(all(target_os = "macos", target_arch = "aarch64"))]
mod host {
    use super::StatBuffer;
    unsafe extern "C" {
        #[link_name = "open"] fn c_open(path: *const std::ffi::c_char, flags: i32, ...) -> i32;
        #[link_name = "write"] fn c_write(fd: i32, bytes: *const std::ffi::c_void, size: usize) -> isize;
        #[link_name = "close"] fn c_close(fd: i32) -> i32;
        #[link_name = "fcntl"] fn c_fcntl(fd: i32, command: i32, ...) -> i32;
        #[link_name = "fstat"] fn c_fstat(fd: i32, output: *mut StatBuffer) -> i32;
        fn __error() -> *mut i32;
    }
    fn invoke<T>(prior: i32, call: impl FnOnce() -> T) -> (T, i32) {
        // Preserve actual native success-errno behavior as well as failures.
        // No intervening allocation/formatting/cleanup may obscure this value.
        unsafe {
            let error = __error();
            let saved = *error;
            *error = prior;
            let result = call();
            let after = *error;
            *error = saved;
            (result, after)
        }
    }
    pub(super) fn open(path: &[u8], flags: i32, mode: Option<i32>, prior: i32) -> Result<(i32, i32), String> {
        Ok(invoke(prior, || unsafe { match mode {
            Some(mode) => c_open(path.as_ptr().cast(), flags, mode),
            None => c_open(path.as_ptr().cast(), flags),
        } }))
    }
    pub(super) fn write(fd: i32, bytes: &[u8], prior: i32) -> Result<(isize, i32), String> {
        Ok(invoke(prior, || unsafe { c_write(fd, bytes.as_ptr().cast(), bytes.len()) }))
    }
    pub(super) fn stat(fd: i32, output: &mut StatBuffer, prior: i32) -> Result<(i32, i32), String> {
        Ok(invoke(prior, || unsafe { c_fstat(fd, output) }))
    }
    pub(super) fn close(fd: i32, prior: i32) -> Result<(i32, i32), String> {
        Ok(invoke(prior, || unsafe { c_close(fd) }))
    }
    pub(super) fn get_fd(fd: i32, prior: i32) -> Result<(i32, i32), String> {
        Ok(invoke(prior, || unsafe { c_fcntl(fd, 1) }))
    }
}

#[cfg(not(all(target_os = "macos", target_arch = "aarch64")))]
mod host {
    pub(super) fn open(_: &[u8], _: i32, _: Option<i32>, _: i32) -> Result<(i32, i32), String> { Err("descriptor host unavailable".into()) }
    pub(super) fn write(_: i32, _: &[u8], _: i32) -> Result<(isize, i32), String> { Err("descriptor host unavailable".into()) }
    pub(super) fn stat(_: i32, _: &mut super::StatBuffer, _: i32) -> Result<(i32, i32), String> { Err("descriptor host unavailable".into()) }
    pub(super) fn close(_: i32, _: i32) -> Result<(i32, i32), String> { Err("descriptor host unavailable".into()) }
    pub(super) fn get_fd(_: i32, _: i32) -> Result<(i32, i32), String> { Err("descriptor host unavailable".into()) }
}

#[cfg(test)]
mod tests;

#[cfg(test)]
mod stat_tests;
