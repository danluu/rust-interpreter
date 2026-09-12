#![allow(dead_code)]

#[inline(never)]
fn mix(value: u64) -> u64 {
    value.rotate_left(9).wrapping_mul(0x9e3779b97f4a7c15)
}

#[inline(never)]
fn recursive(value: u64) -> u64 {
    if value == 0 {
        3
    } else {
        value.wrapping_add(recursive(value - 1))
    }
}

#[inline(never)]
fn pointer_read(value: &u64) -> u64 {
    *value
}

#[inline(never)]
fn pointer_write(value: &mut u64, input: u64) {
    *value = input.wrapping_add(17);
}

struct Projected(u64);

#[inline(never)]
fn projected(value: Projected) -> u64 {
    value.0
}

#[track_caller]
#[inline(never)]
fn tracked(value: u64) -> u64 {
    value.wrapping_add(29)
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut value = mix(seed);
    value = mix(value);
    let input = seed ^ value;
    pointer_write(&mut value, input);
    value = value.wrapping_add(pointer_read(&value));
    value = value.wrapping_add(projected(Projected(seed.rotate_right(7))));
    value = value.wrapping_add(recursive(seed & 7));
    tracked(value)
}

#[test]
fn scalar_assertions() {
    assert_eq!(recursive(7), 31);
    assert_eq!(rust_interp_entry(0), 66);
    assert_eq!(pointer_read(&123), 123);
    let mut value = 1;
    pointer_write(&mut value, 9);
    assert_eq!(value, 26);
    assert_eq!(projected(Projected(19)), 19);
    assert_eq!(tracked(23), 52);
}

fn main() {
    for value in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(value.parse().unwrap()));
    }
}
