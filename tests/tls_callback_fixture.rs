use std::sync::atomic::{AtomicU64, Ordering};
static DROPS: AtomicU64 = AtomicU64::new(0);
unsafe extern "C" { fn _tlv_atexit(callback: unsafe extern "C" fn(*mut u8), argument: *mut u8); }

unsafe extern "C" fn callback(argument: *mut u8) {
    match argument as usize {
        2 => assert_eq!(DROPS.swap(2, Ordering::Relaxed), 0),
        1 => assert_eq!(DROPS.swap(21, Ordering::Relaxed), 2),
        _ => panic!("unexpected TLS callback argument"),
    }
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    assert_eq!(DROPS.load(Ordering::Relaxed), 0);
    unsafe {
        _tlv_atexit(callback, 1usize as *mut u8);
        _tlv_atexit(callback, 2usize as *mut u8);
    }
    seed.rotate_left(13) ^ 42
}

#[test]
fn a_register() { assert_eq!(rust_interp_entry(0), 42); }
#[test]
fn b_after_cleanup() { assert_eq!(DROPS.load(Ordering::Relaxed), 21); }

fn main() {
    let seed: u64 = std::env::args().nth(1).unwrap().parse().unwrap();
    // Joining makes native thread-exit callbacks observable to this control.
    let result = std::thread::spawn(move || rust_interp_entry(seed)).join().unwrap();
    assert_eq!(DROPS.load(Ordering::Relaxed), 21);
    println!("{result}");
}
