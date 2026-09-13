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
fn arithmetic(mut x: u32) -> u32 {
    x += 1; x -= 1; x *= 2; x /= 2; x %= 100; x ^= 1; x &= 255; x |= 2; x <<= 1; x >>= 1; x
}
fn literals() -> (bool, u8, char, u128, f64, &'static str, &'static [u8], &'static core::ffi::CStr) {
    (true, b'a', 'λ', 340282366920938463463374607431768211455_u128,
        1.25e2_f64, r#"raw λ"#, br#"bytes"#, c"nul")
}
fn unsafe_block(x: *const u32) -> u32 { unsafe { *x } }
fn flow(mut x: i32, stop: bool) -> i32 {
    if !stop && x > 0 { x = -x; }
    if stop { return x; }
    x
}
fn early(stop: bool) { if stop { return; } let _ = (); }
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
    assert_eq!(arithmetic(4), 7);
    let literals = literals();
    assert_eq!(literals.0, true); assert_eq!(literals.1, b'a'); assert_eq!(literals.2, 'λ');
    assert_eq!(literals.3, u128::MAX); assert_eq!(literals.4, 125.0);
    assert_eq!(literals.5, "raw λ"); assert_eq!(literals.6, b"bytes"); assert_eq!(literals.7, c"nul");
    assert_eq!(unsafe_block(&4), 4);
    assert_eq!(flow(5, false), -5); assert_eq!(flow(5, true), 5);
    early(true); early(false);
    assert_eq!(body_type(&4), 4);
    assert_eq!(nested(), 1);
    assert_eq!(closure(), 1);
    println!("{} {} {} {} {}", current::selected(&value), value.method(), value.double(),
        conditional(&value, true), expansion());
}
