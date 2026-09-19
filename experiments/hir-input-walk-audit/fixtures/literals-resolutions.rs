#![allow(dead_code, unused_imports)]

fn escaped_literals() -> (&'static str, &'static [u8], &'static core::ffi::CStr, char, u8) {
    ("line\n\t\u{03bb}\\\"", b"\x00\n\xff", c"\u{03bb}\xff", '\n', b'\x7f')
}
fn raw_literals() -> (&'static str, &'static [u8], &'static core::ffi::CStr) {
    (r#"raw \n λ"#, br#"raw \x00"#, cr#"raw \n λ"#)
}
fn underscored_numbers() -> (u128, f64, u32, u32, u32) {
    (18_446_744_073_709_551_616_u128, 1_2.5_0e+1_f64, 0xAB_CD_u32, 0o7_5_5_u32, 0b10_01_u32)
}
fn local_patterns(mut x: u32) -> u32 {
    let _ = x;
    let ref mut y = x;
    *y += 1;
    let z = { let x = *y + 2; x };
    z + *y
}
const OFFSET: u32 = 3;
static STATIC_OFFSET: u32 = 4;
fn definitions(x: u32) -> u32 { x + OFFSET + STATIC_OFFSET }
fn local_call(x: u32) -> u32 { definitions(x) }
fn external_constant() -> f32 { std::f32::consts::PI }
struct Pair(u32);
fn local_constructor(x: u32) -> Pair { Pair(x) }
struct Meter { value: u32 }
trait First { fn measure(&self) -> u32; }
trait Second { fn measure(&self) -> u32; }
impl First for Meter { fn measure(&self) -> u32 { self.value + 1 } }
impl Second for Meter { fn measure(&self) -> u32 { self.value + 2 } }
mod selection {
    use super::{First as Selected, Meter};
    pub(super) fn trait_selection(x: &Meter) -> u32 { x.measure() }
}
fn main() {
    let escaped = escaped_literals();
    assert_eq!(escaped.0, "line\n\tλ\\\"");
    assert_eq!(escaped.1, &[0, 10, 255]);
    assert_eq!(escaped.2.to_bytes(), &[0xce, 0xbb, 255]);
    assert_eq!((escaped.3, escaped.4), ('\n', 127));
    let raw = raw_literals();
    assert_eq!(raw.0, "raw \\n λ");
    assert_eq!(raw.1, b"raw \\x00");
    assert_eq!(raw.2.to_bytes(), "raw \\n λ".as_bytes());
    assert_eq!(underscored_numbers(), (18_446_744_073_709_551_616, 125.0, 43981, 493, 9));
    assert_eq!(local_patterns(4), 12);
    assert_eq!(local_call(5), 12);
    assert_eq!(external_constant(), std::f32::consts::PI);
    assert_eq!(local_constructor(5).0, 5);
    let meter = Meter { value: 7 };
    assert_eq!(selection::trait_selection(&meter), 8);
}
