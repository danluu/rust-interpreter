use std::convert::Infallible;
unsafe extern "C" { fn absent_uninhabited_branch() -> u64; }
// Native debug code retains the external reference even for an impossible
// variant. Supply a fail-fast native link target. The custom exporter still
// treats the foreign declaration as unsupported if its call is reachable.
#[unsafe(export_name="absent_uninhabited_branch")]
pub extern "C" fn native_uninhabited_guard() -> u64 { panic!("entered an impossible variant") }
enum State<T> { Left(u64), Right(u64), Missing(T) }
#[inline(never)]
fn state<T>(value: State<T>) -> u64 {
    match value {
        State::Left(v) => v.rotate_left(7),
        State::Right(v) => v.rotate_right(9),
        State::Missing(_) => unsafe { absent_uninhabited_branch() },
    }
}
#[repr(i16)]
enum Tagged<T> { Left = -9, Right = 12, Missing(T) = 21 }
#[inline(never)]
fn tagged<T>(value: Tagged<T>) -> u64 {
    match value {
        Tagged::Left => 19,
        Tagged::Right => 53,
        Tagged::Missing(_) => unsafe { absent_uninhabited_branch() },
    }
}
#[inline(never)]
fn nested(value: Option<Result<u64, Infallible>>) -> u64 {
    match value { None => 11, Some(Ok(value)) => value, Some(Err(_)) => unsafe { absent_uninhabited_branch() } }
}
#[allow(non_snake_case)]
fn CCRandomGenerateBytes(p: *mut u8, n: usize) -> i32 {
    assert_eq!(n, 1);
    unsafe { *p = 123; }
    17
}
fn abort() -> u64 { 41 }
pub fn rust_interp_entry(seed: u64) -> u64 {
    let value: State<Infallible> = if seed & 1 == 0 { State::Left(seed) } else { State::Right(seed) };
    let tag: Tagged<Infallible> = if seed & 2 == 0 { Tagged::Left } else { Tagged::Right };
    let mut byte = 0;
    assert_eq!(CCRandomGenerateBytes(&mut byte, 1), 17);
    assert_eq!(byte, 123);
    state(value) ^ tagged(tag) ^ nested(if seed & 4 == 0 { None } else { Some(Ok(seed)) }) ^ abort()
}
fn main() {
    for arg in std::env::args().skip(1) { println!("{}",rust_interp_entry(arg.parse().unwrap())); }
}
