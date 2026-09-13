#![allow(dead_code)]

pub fn anchor(x: u64) -> u64 { let doubled = x * 2; doubled + 3 }
pub fn changed(x: u64) -> u64 { x + 1 }
pub fn unit() {}
pub fn scalar(x: f64) -> f64 { x * 1.5 }
pub fn calls(x: u64) -> u64 { anchor(x) }
pub fn generic<T: Copy>(x: T) -> T { x }
#[inline(never)]
pub fn attributed(x: u64) -> u64 { x + 7 }
pub fn expands() -> u32 { line!() }
pub struct Value(u64);
impl Value { pub fn method(&self) -> u64 { self.0 } }

#[cfg(type_error)]
fn uncalled_type_error() -> u64 { true }
#[cfg(borrow_error)]
fn uncalled_borrow_error() { let value = String::from("a"); let moved = value; drop(value); }
#[cfg(const_error)]
const UNCALLED_CONST_ERROR: u64 = 1 / 0;
#[cfg(panic_error)]
fn uncalled_panic_error() -> u64 { 1 / 0 }

fn main() {
    assert_eq!(anchor(5), 13);
    assert_eq!(changed(5), 6);
    assert_eq!(scalar(2.0), 3.0);
    assert_eq!(calls(5), 13);
    assert_eq!(generic(4_u8), 4);
    assert_eq!(attributed(1), 8);
    assert_eq!(Value(9).method(), 9);
    unit();
    println!("{} {} {}", anchor(5), changed(5), expands());
}
