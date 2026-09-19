#![allow(dead_code, unused)]

fn rejected_typed_local(x: u32) -> u32 { let y: u32 = x; y }
fn rejected_nested_item() -> u32 { fn inner() -> u32 { 1 } inner() }
fn rejected_closure() -> u32 { let f = || 1; f() }
fn rejected_match(x: Option<u32>) -> u32 { match x { Some(x) => x, None => 0 } }
fn rejected_tuple_pattern((x, y): (u32, u32)) -> u32 { x + y }
async fn rejected_coroutine() -> u32 { 1 }
fn identity<T>(x: T) -> T { x }
fn rejected_type_arguments() -> u32 { identity::<u32>(1) }
fn rejected_external_call(x: &u32, y: &u32) -> bool { std::ptr::eq(x, y) }
macro_rules! generated { () => { 1 + 2 }; }
fn rejected_hygiene() -> u32 { generated!() }
fn main() {
    assert_eq!(rejected_typed_local(2), 2);
    assert_eq!(rejected_nested_item(), 1);
    assert_eq!(rejected_closure(), 1);
    assert_eq!(rejected_match(Some(3)), 3);
    assert_eq!(rejected_tuple_pattern((2, 3)), 5);
    assert_eq!(rejected_type_arguments(), 1);
    let x = 1;
    assert!(rejected_external_call(&x, &x));
    assert_eq!(rejected_hygiene(), 3);
}
