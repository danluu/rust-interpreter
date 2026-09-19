#![allow(dead_code)]

#[inline(never)]
pub fn changing_value() -> u32 {
    3 // changed body
}

#[inline(never)]
pub fn unchanged(value: u32) -> u32 {
    let values = [value, value + 1];
    let borrowed = &values;
    borrowed.iter().copied().sum()
}

pub fn opaque_value() -> u32 {
    17
}

fn main() {
    println!("{}:{}:{}", changing_value(), unchanged(2), opaque_value());
}
