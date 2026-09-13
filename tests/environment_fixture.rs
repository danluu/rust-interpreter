use std::ffi::{CStr, OsStr};
use std::os::unix::ffi::OsStrExt;

unsafe extern "C" {
    fn getenv(name: *const std::ffi::c_char) -> *mut std::ffi::c_char;
    fn strlen(value: *const std::ffi::c_char) -> usize;
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    // The driver supplies these exact synthetic values to both native and VM
    // children. Never print or inspect unrelated ambient environment values.
    let text = std::env::var("RI_ENV_TEXT").unwrap();
    assert_eq!(text, "hello=λ");
    assert_eq!(std::env::var("RI_ENV_EMPTY").unwrap(), "");
    assert_eq!(std::env::var("RI_ENV_MISSING"), Err(std::env::VarError::NotPresent));
    let raw = std::env::var_os("RI_ENV_RAW").unwrap();
    assert_eq!(raw.as_bytes(), &[0x80, b'=', 0xfe]);
    assert_eq!(std::env::var("RI_ENV_RAW"), Err(std::env::VarError::NotUnicode(raw.clone())));
    assert_eq!(std::env::var_os(OsStr::from_bytes(b"RI_ENV_\xff")).unwrap(), OsStr::from_bytes(b"raw-name"));
    assert!(std::env::var_os("").is_none());
    assert!(std::env::var_os("invalid=name").is_none());
    assert!(std::env::var_os(OsStr::from_bytes(b"RI_ENV_TEXT\0tail")).is_none());
    unsafe {
        let first = getenv(c"RI_ENV_TEXT".as_ptr());
        assert!(!first.is_null());
        let second = getenv(c"RI_ENV_EMPTY".as_ptr());
        assert!(!second.is_null());
        assert_eq!(CStr::from_ptr(second).to_bytes(), b"");
        assert_eq!(first, getenv(c"RI_ENV_TEXT".as_ptr()));
        assert_eq!(CStr::from_ptr(first).to_bytes(), text.as_bytes());
        assert_eq!(strlen(std::hint::black_box(first)), text.len());
        assert_eq!(strlen(std::hint::black_box(second)), 0);
        assert!(getenv(c"RI_ENV_MISSING".as_ptr()).is_null());
    }
    // Move returned owned values through ordinary Rust allocations and drops.
    let joined = [text.as_bytes(), raw.as_bytes()].concat();
    joined.iter().fold(seed, |state, &byte| state.rotate_left(7) ^ byte as u64)
}

// Invalid foreign pointers are tested only in the custom engines, whose
// contract is a guest memory error. Never call this entry in the native control.
pub fn invalid_strlen(pointer: u64) -> u64 {
    unsafe { strlen(pointer as *const std::ffi::c_char) as u64 }
}

fn main() {
    for seed in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(seed.parse().unwrap()));
    }
}
