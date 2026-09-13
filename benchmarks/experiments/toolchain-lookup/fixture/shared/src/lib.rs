#![no_std]

#[inline(never)]
pub fn shared_value(x: u64) -> u64 {
    x + 7
}
