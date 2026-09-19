#![allow(dead_code)]

#[inline(always)]
fn changing_value() -> u32 {
    3 // changed body
}

#[inline(never)]
fn opaque_value() -> u32 {
    changing_value()
}

#[warn(unused_mut)]
#[inline(never)]
fn warning_value() -> u32 {
    let mut warning_token = changing_value();
    warning_token
}

#[deny(unfulfilled_lint_expectations)]
#[expect(unused_mut)]
#[inline(never)]
fn expectation_value() -> u32 {
    let mut expected_unused_mut = changing_value();
    expected_unused_mut
}

#[test]
fn selected() {
    assert!(changing_value() > 0);
    assert!(opaque_value() == changing_value());
    assert!(warning_value() == changing_value());
    assert!(expectation_value() == changing_value());
}
