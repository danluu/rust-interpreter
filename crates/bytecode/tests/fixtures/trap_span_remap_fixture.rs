#![feature(panic_internals)]
#![allow(dead_code, internal_features)]

macro_rules! fail { ($message:literal) => { core::panicking::panic($message) }; }

#[inline(never)]
pub fn fast_path() -> u64 {
    fail!("fast trap")
}

#[inline(never)]
pub fn slow_path(cell: &mut u64) -> u64 {
    *cell = 29;
    core::panicking::panic("slow trap")
}

#[inline(never)]
fn observed_file() -> &'static str { file!() }

#[inline(never)]
fn observed_caller() -> &'static std::panic::Location<'static> {
    std::panic::Location::caller()
}

fn hash_file(file: &str, mut hash: u64) -> u64 {
    for byte in file.bytes() { hash = hash.rotate_left(5) ^ byte as u64; }
    hash
}

pub fn rust_interp_entry(case: u64) -> u64 {
    match case {
        0 => fast_path(),
        1 => { let mut cell = 0; slow_path(&mut cell) },
        _ => {
            let location = observed_caller();
            hash_file(observed_file(), hash_file(location.file(),
                ((location.line() as u64) << 32) | location.column() as u64))
        }
    }
}

#[cfg(native)]
fn main() {
    let case: u64 = std::env::args().nth(1).unwrap().parse().unwrap();
    if case == 2 {
        let location = observed_caller();
        println!("file\t{}", observed_file());
        println!("caller\t{}\t{}\t{}", location.file(), location.line(), location.column());
        println!("value\t{}", rust_interp_entry(2));
    } else {
        std::panic::set_hook(Box::new(|info| {
            let location = info.location().unwrap();
            println!("panic\t{}\t{}\t{}", location.file(), location.line(), location.column());
        }));
        let mut cell = 0;
        let failure = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            if case == 0 { fast_path() } else { slow_path(&mut cell) }
        }));
        assert!(failure.is_err());
        assert_eq!(cell, if case == 0 { 0 } else { 29 });
        println!("cell\t{cell}");
    }
}
