//! Read-only Darwin CPU-feature queries using checked guest buffers.
use super::Memory;

impl Memory {
    pub(super) fn cpu_feature_query(
        &mut self, name: usize, output: usize, output_len: usize,
        new_data: usize, new_len: usize,
    ) -> Result<u128, String> {
        if new_data != 0 || new_len != 0 {
            return Err("CPU-feature query does not support writes".into());
        }
        let mut bytes = [0u8; 128];
        let mut end = None;
        for (index, byte) in bytes.iter_mut().enumerate() {
            let at = name.checked_add(index).ok_or("CPU-feature name address overflow")?;
            *byte = self.read(at, 1)?[0];
            if *byte == 0 { end = Some(index); break; }
        }
        let end = end.ok_or("CPU-feature name exceeds 127 bytes")?;
        let key = &bytes[..end];
        let feature = key.strip_prefix(b"hw.optional.arm.FEAT_")
            .is_some_and(|suffix| !suffix.is_empty()
                && suffix.iter().all(|b| b.is_ascii_alphanumeric() || *b == b'_'));
        if !feature && !matches!(key, b"hw.cpufamily" | b"hw.optional.floatingpoint" | b"hw.optional.AdvSIMD"
            | b"hw.optional.arm.AdvSIMD" | b"hw.optional.armv8_crc32") {
            return Err(format!("unsupported CPU-feature query name: {:?}", String::from_utf8_lossy(key)));
        }
        // std_detect uses exactly one i32 and a separate usize length. Other
        // sysctl buffer modes remain unsupported rather than partially emulated.
        if self.load(output_len, 8)? != 4 {
            return Err("CPU-feature query requires a four-byte output buffer".into());
        }
        let (value_heap, value_range) = self.range(output, 4)?;
        let (length_heap, length_range) = self.range(output_len, 8)?;
        if (!value_heap && output < self.readonly_end)
            || (!length_heap && output_len < self.readonly_end) {
            return Err("write to read-only guest memory".into());
        }
        if value_heap == length_heap
            && value_range.start < length_range.end && length_range.start < value_range.end {
            return Err("CPU-feature output and length buffers overlap".into());
        }
        #[cfg(target_os = "macos")]
        {
            unsafe extern "C" {
                fn sysctlbyname(name: *const std::ffi::c_char, old: *mut std::ffi::c_void,
                                len: *mut usize, new: *mut std::ffi::c_void, new_len: usize) -> i32;
            }
            // Local host storage preserves untouched bytes if the OS returns an
            // error. Guest addresses never cross the FFI boundary. All guest
            // destinations have been validated before any output is changed.
            let mut value = self.load(output, 4)? as u32;
            let mut length = 4usize;
            let status = unsafe { sysctlbyname(bytes.as_ptr().cast(), (&mut value as *mut u32).cast(),
                                               &mut length, std::ptr::null_mut(), 0) };
            self.store(output, 4, value as u128)?;
            self.store(output_len, 8, length as u128)?;
            Ok(status as u32 as u128)
        }
        #[cfg(not(target_os = "macos"))]
        Err("CPU-feature query requires macOS".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::heap;

    fn memory() -> Memory {
        let mut m = Memory { bytes: vec![0; 384], heap: heap::Heap::default(),
                             limit: 4096, readonly_end: 144, peak: 768, auxiliary_bytes: 0 };
        m.heap.bytes.resize(384, 0);
        let key = b"hw.optional.arm.FEAT_AES\0";
        m.bytes[16..16+key.len()].copy_from_slice(key);
        m.store(200, 8, 4).unwrap();
        m.store(216, 4, 0x12345678).unwrap();
        m
    }

    #[test]
    fn invalid_queries_leave_both_arenas_unchanged() {
        // Invalid names, missing terminators, outputs, lengths and writes must
        // fail before the host query can affect either guest arena.
        for mode in 0..15 {
            let mut m = memory();
            let (mut name, mut out, mut len, mut new, mut new_len) = (16, 216, 200, 0, 0);
            match mode {
                0 => new = 1,
                1 => new_len = 1,
                2 => name = 0,
                3 => name = usize::MAX,
                4 => { m.bytes[16..144].fill(b'a'); },
                5 => { m.bytes[16] = b'X'; },
                6 => out = 0,
                7 => out = 383,
                8 => out = 16,
                9 => { m.bytes[128..136].copy_from_slice(&4u64.to_le_bytes()); len = 128; },
                10 => out = 200,
                11 => out = heap::TAG + 383,
                12 => len = 383,
                13 => m.store(200, 8, 3).unwrap(),
                14 => m.store(200, 8, 8).unwrap(),
                _ => unreachable!(),
            }
            let before = (m.bytes.clone(), m.heap.bytes.clone());
            assert!(m.cpu_feature_query(name, out, len, new, new_len).is_err(), "{mode}");
            assert_eq!((m.bytes, m.heap.bytes), before, "{mode}");
        }
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn actual_queries_match_native_status_value_and_length_in_both_arenas() {
        unsafe extern "C" {
            fn sysctlbyname(name: *const std::ffi::c_char, old: *mut std::ffi::c_void,
                            len: *mut usize, new: *mut std::ffi::c_void, new_len: usize) -> i32;
        }
        for key in [c"hw.optional.arm.FEAT_AES", c"hw.cpufamily", c"hw.optional.arm.FEAT_RUST_INTERP_MISSING"] {
            let mut value = 0x12345678u32;
            let mut length = 4usize;
            let status = unsafe { sysctlbyname(key.as_ptr(), (&mut value as *mut u32).cast(),
                                               &mut length, std::ptr::null_mut(), 0) };
            for name_heap in [false, true] {
                for output_heap in [false, true] {
                    for length_heap in [false, true] {
                        let mut m = memory();
                        let name = 16 + if name_heap { heap::TAG } else { 0 };
                        let out = 216 + if output_heap { heap::TAG } else { 0 };
                        let len = 200 + if length_heap { heap::TAG } else { 0 };
                        let target = if name_heap { &mut m.heap.bytes } else { &mut m.bytes };
                        target[16..16+key.to_bytes_with_nul().len()].copy_from_slice(key.to_bytes_with_nul());
                        m.store(out, 4, 0x12345678).unwrap(); m.store(len, 8, 4).unwrap();
                        assert_eq!(m.cpu_feature_query(name, out, len, 0, 0).unwrap(), status as u32 as u128);
                        assert_eq!(m.load(out, 4).unwrap(), value as u128);
                        assert_eq!(m.load(len, 8).unwrap(), length as u128);
                    }
                }
            }
        }
    }
}
