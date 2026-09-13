#![allow(dead_code)]

fn changing_value() -> u32 {
    3 // changed body
}

#[inline(never)]
fn old_ordinary(value: u32) -> u32 {
    let values = [value, value + 1];
    let borrowed = &values;
    borrowed[0] + borrowed[1]
}

#[inline(never)]
fn old_opaque() -> u32 {
    17u32
}

#[warn(unused_mut)]
#[inline(never)]
fn old_warning() -> u32 {
    let mut warning_token = 7;
    warning_token
}

#[deny(unfulfilled_lint_expectations)]
#[expect(unused_mut)]
#[inline(never)]
fn old_expectation() -> u32 {
    let mut expected_unused_mut = 11;
    expected_unused_mut
}

fn main() {
    let sum = changing_value(); // selected calls
    println!("{}", sum);
}
