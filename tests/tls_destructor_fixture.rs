use std::cell::RefCell;
use std::sync::atomic::{AtomicU64, Ordering};

static DROPS: AtomicU64 = AtomicU64::new(0);
struct Token(u64);
impl Drop for Token {
    fn drop(&mut self) {
        let previous = DROPS.load(Ordering::Relaxed);
        match self.0 {
            2 => assert!(previous == 0 || previous % 1000 == 231),
            3 => assert_eq!(previous % 10, 2),
            1 => assert_eq!(previous % 100, 23),
            _ => panic!("unexpected destructor"),
        }
        DROPS.store(previous * 10 + self.0, Ordering::Relaxed);
        // Valid reentrancy: Rust adds this newly initialized TLS value to its
        // own destructor list while its already registered callback runs.
        if self.0 == 2 { LATE.with(|value| assert_eq!(value.borrow().len(), 1)); }
    }
}
thread_local! {
    static FIRST: RefCell<Vec<Token>> = RefCell::new(vec![Token(1)]);
    static SECOND: RefCell<Vec<Token>> = RefCell::new(vec![Token(2)]);
    static LATE: RefCell<Vec<Token>> = RefCell::new(vec![Token(3)]);
}
fn initialize() {
    FIRST.with(|value| assert_eq!(value.borrow().len(), 1));
    SECOND.with(|value| assert_eq!(value.borrow().len(), 1));
}
pub fn rust_interp_entry(seed: u64) -> u64 {
    assert_eq!(DROPS.load(Ordering::Relaxed), 0);
    initialize();
    seed.rotate_left(7) ^ 79
}
pub fn try_entry(seed: u64) -> u64 {
    std::panic::catch_unwind(|| {
        let mut values = vec![seed, seed.wrapping_add(17), seed ^ 3];
        values.reverse();
        values[0].wrapping_add(values[2])
    }).unwrap()
}
pub fn panic_entry(_: u64) -> u64 {
    // Native returns 91. The experimental guest path must fail this command;
    // it cannot manufacture either a successful return or a caught exception.
    if std::panic::catch_unwind(|| panic!("try callback failed")).is_err() { 91 } else { 0 }
}
#[test]
fn a_first() { initialize(); }
#[test]
fn b_after_first() {
    assert_eq!(DROPS.load(Ordering::Relaxed), 231);
    initialize();
}
#[test]
fn c_after_second() { assert_eq!(DROPS.load(Ordering::Relaxed), 231231); }
#[test]
fn d_final_test() { initialize(); }

fn main() {
    let mut args = std::env::args().skip(1);
    let name = args.next().unwrap();
    let seed = args.next().unwrap().parse().unwrap();
    let value = match name.as_str() {
        "tls" => {
            let value = std::thread::spawn(move || rust_interp_entry(seed)).join().unwrap();
            assert_eq!(DROPS.load(Ordering::Relaxed), 231);
            value
        }
        "try" => try_entry(seed),
        "panic" => panic_entry(seed),
        _ => panic!("unexpected entry"),
    };
    println!("{value}");
}
