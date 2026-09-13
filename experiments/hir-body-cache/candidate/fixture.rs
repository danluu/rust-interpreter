#![allow(dead_code, unused_imports)]
#![deny(unconditional_panic)]

struct Counter { value: u32 }
trait Left { fn choose(&self) -> u32; }
trait Right { fn choose(&self) -> u32; }
impl Left for Counter { fn choose(&self) -> u32 { self.value + 10 } }
impl Right for Counter { fn choose(&self) -> u32 { self.value + 20 } }
mod current {
    use super::{Counter, Left as Selected};
    pub(super) fn selected(x: &Counter) -> u32 { x.choose() }
}
impl Counter {
    #[inline]
    fn add(&mut self, x: u32) { self.value += x; }
    fn field(&self) -> u32 { self.value }
    fn method(&self) -> u32 { self.field() + 1 }
}
trait DefaultBody {
    fn field(&self) -> u32;
    fn double(&self) -> u32 { self.field() + self.field() }
}
impl DefaultBody for Counter { fn field(&self) -> u32 { self.value } }

fn anchor(x: u32) -> u32 { let y = (x + 1); ; y * 2 }
fn changed(x: u32) -> u32 { x + 3 }
fn local_call(x: u32) -> u32 { anchor(x) }
fn shadow(x: u32) -> u32 { let y = { let x = x + 1; x }; y + x }
fn conditional(x: &Counter, yes: bool) -> u32 { if yes { x.value } else { 0 } }
fn array_index(x: u32) -> u32 { let a = [x, x + 1]; a[1] }
fn generic<T: Copy>(x: T) -> T { x }
fn borrowed(x: &u32) -> u32 { *x }
fn raw(x: &u32) -> *const u32 { &raw const *x }
fn uninitialized(x: u32) -> u32 { let y; y = x; y }
fn body_type(x: &u32) -> u32 { let y: &u32 = x; *y }
fn nested() -> u32 { fn child() -> u32 { 1 } child() }
fn closure() -> u32 { let f = || 1; f() }
fn expansion() -> u32 { line!() }

#[cfg(type_error)] fn uncalled_type() -> u32 { true }
#[cfg(borrow_error)] fn uncalled_borrow() { let x = String::from("used"); let y = x; drop(x); }
#[cfg(const_error)] const BAD_CONST: u32 = 1 / 0;
#[cfg(panic_error)] fn uncalled_panic() -> u32 { 1 / 0 }

fn main() {
    let mut value = Counter { value: 2 };
    value.add(changed(1));
    assert_eq!(anchor(4), 10);
    assert_eq!(local_call(4), 10);
    assert_eq!(shadow(4), 9);
    assert_eq!(array_index(4), 5);
    assert_eq!(generic(4_u8), 4);
    assert_eq!(borrowed(&4), 4);
    assert_eq!(unsafe { *raw(&4) }, 4);
    assert_eq!(uninitialized(4), 4);
    assert_eq!(body_type(&4), 4);
    assert_eq!(nested(), 1);
    assert_eq!(closure(), 1);
    println!("{} {} {} {} {}", current::selected(&value), value.method(), value.double(),
        conditional(&value, true), expansion());
}
