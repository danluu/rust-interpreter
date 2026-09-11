#![feature(integer_cast_extras)]

// Keep similarly named user functions ordinary. Only helpers in the compiler's
// actual core crate may be recognized as integer-overflow panic routines.
mod core {
    pub mod num {
        pub mod imp {
            pub mod overflow_panic {
                pub fn pow(a: u64) -> u64 { a.wrapping_add(9) }
            }
        }
    }
}

pub fn rust_interp_entry(case: u64, value: u64) -> u64 {
    match case {
        0 => value.strict_pow(2),
        1 => value.strict_add(1),
        2 => value.strict_sub(1),
        3 => value.strict_mul(2),
        4 => (value as i64).strict_neg() as u64,
        5 => value.strict_shl(1),
        6 => 1u64.strict_shr(value as u32),
        7 => (value as i64).strict_rem(-1) as u64,
        8 => core::num::imp::overflow_panic::pow(value),
        10 => value.strict_cast_signed() as u64,
        11 => value.ilog10() as u64,
        12 => value.ilog2() as u64,
        13 => value.ilog(3) as u64,
        _ => 1u64.strict_shl(value as u32),
    }
}

fn main() {
    let mut args = std::env::args().skip(1);
    println!("{}",rust_interp_entry(args.next().unwrap().parse().unwrap(),args.next().unwrap().parse().unwrap()));
}
