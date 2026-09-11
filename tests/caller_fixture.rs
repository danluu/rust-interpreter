use std::panic::Location;

fn encode(location: &Location<'_>) -> u64 {
    let mut hash = ((location.line() as u64) << 32) | location.column() as u64;
    for byte in location.file().bytes() { hash = hash.rotate_left(5) ^ byte as u64; }
    hash
}

#[track_caller]
#[inline(never)]
fn tracked() -> u64 { encode(Location::caller()) }

#[track_caller]
#[inline(never)]
fn forwarded() -> u64 { tracked() }

#[inline(never)]
fn untracked() -> u64 { forwarded() }

#[track_caller]
#[inline(never)]
fn recursive(depth: u64) -> u64 {
    if depth == 0 { tracked() } else { recursive(depth - 1) }
}

#[track_caller]
#[inline(always)]
fn inlined_tracked() -> u64 { tracked() }

#[inline(always)]
fn inlined_untracked() -> u64 { tracked() }

trait ReadLocation {
    #[track_caller]
    fn read(&self, seed: u64) -> u64;
}
struct Reader;
impl ReadLocation for Reader {
    fn read(&self, seed: u64) -> u64 { tracked() ^ seed }
}

#[track_caller]
fn generic<T: ReadLocation + ?Sized>(value: &T, seed: u64) -> u64 { value.read(seed) }

macro_rules! locate { () => { tracked() }; }

pub fn rust_interp_entry(seed: u64) -> u64 {
    let a = tracked();
    let b = forwarded();
    assert_ne!(a, b);
    let pointer: fn() -> u64 = std::hint::black_box(tracked);
    let reader = Reader;
    let dynamic: &dyn ReadLocation = &reader;
    // Report one case per input so a location/ABI mismatch names its case.
    let values = [a, b, pointer(), untracked(), recursive(seed % 5),
        inlined_tracked(), inlined_untracked(), locate!(), generic(&reader, seed),
        generic(dynamic, seed.rotate_left(7)), dynamic.read(seed)];
    values[seed as usize % values.len()]
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
