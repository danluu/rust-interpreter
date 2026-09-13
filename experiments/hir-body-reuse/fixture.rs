#![allow(dead_code)]
#![deny(unconditional_panic)]
extern crate external;
use external::Left as Selected;

struct Counter { value: u32 }
trait ReadCounter { fn read(&self) -> u32; }
impl Counter {
    #[inline]
    fn add(&mut self, amount: u32) { self.value += amount; }
    fn read_inherent(&self) -> u32 { self.value }
    fn twice(&self) -> u32 { self.read_inherent() + self.read_inherent() }
}
impl ReadCounter for Counter { fn read(&self) -> u32 { self.value } }
trait DefaultBody {
    fn read(&self) -> u32;
    fn double(&self) -> u32 { self.read() + self.read() }
}
fn local_value(x: u32) -> u32 { x + 3 }
fn local_call(x: u32) -> u32 { local_value(x) }
fn external_method(x: &external::Foreign) -> u32 { x.selected() }
fn external_call(x: i64) -> i64 { external::identity(x) }
fn external_pointer(x: i64) -> i64 { let f = external::identity; f(x) }
fn via_trait<T: ReadCounter>(x: &T) -> u32 { x.read() }
fn conditional(x: &Counter, yes: bool) -> u32 { if yes { x.value } else { 0 } }
fn array_index(x: u32) -> u32 { let values = [x, x + 1]; values[1] }
fn borrowed(x: &u32) -> u32 { *x }
fn raw(x: &u32) -> *const u32 { &raw const *x }
fn literal() -> &'static str { "retained literal" }
fn return_local(x: u32) -> u32 { let result = x + 1; return result; }
fn nested_definition() -> u32 { fn inner() -> u32 { 1 } inner() }
fn closure() -> u32 { let f = || 1; f() }
fn body_type(x: &u32) -> u32 { let y: &u32 = x; *y }
fn macro_body() -> u32 { assert!(true); 1 }
fn typed_path(x: u32) -> u32 { std::convert::identity::<u32>(x) }

#[cfg(type_error)] fn bad_type() -> u32 { "wrong" }
#[cfg(borrow_error)] fn bad_borrow() { let x = String::from("used"); let _y = x; drop(x); }
#[cfg(const_error)] const BAD_CONST: u32 = 1 / 0;
#[cfg(panic_error)] fn bad_panic() -> u32 { 1 / 0 }

fn main() {
    let mut counter = Counter { value: 4 };
    counter.add(local_call(2));
    assert_eq!(counter.twice(), 18);
    assert_eq!(via_trait(&counter), 9);
    assert_eq!(conditional(&counter, false), 0);
    assert_eq!(external_method(&external::Foreign), 11);
    assert_eq!(external_call(9), 9);
    assert_eq!(external_pointer(13), 13);
    assert_eq!(array_index(4), 5);
    assert_eq!(borrowed(&7), 7);
    assert_eq!(unsafe { *raw(&8) }, 8);
    assert_eq!(literal(), "retained literal");
    assert_eq!(return_local(7), 8);
}
