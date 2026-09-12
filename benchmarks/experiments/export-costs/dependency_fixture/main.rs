mod model;

pub fn rust_interp_entry(seed: u64) -> u64 {
    let record = model::Record { prefix: seed as u8, value: seed ^ 31 };
    assert_eq!(model::stable(seed), seed.rotate_left(9) ^ 17);
    assert_eq!(model::body(seed), seed.wrapping_add(7));
    assert_eq!(model::value(&record), seed ^ 31);
    assert_eq!(record.prefix, seed as u8);
    let generic = model::generic(seed as model::GenericWord);
    assert_eq!(generic, (seed as model::GenericWord as u64).wrapping_mul(model::SCALE));
    model::stable(seed) ^ model::body(seed) ^ model::value(&record)
        ^ model::layout_metric() ^ (model::narrow(seed) as u64) ^ generic
        ^ model::LABEL.iter().fold(0u64, |a, b| a.rotate_left(7) ^ u64::from(*b))
}

fn main() {
    let seed = std::env::args().nth(1).unwrap().parse().unwrap();
    println!("{}", rust_interp_entry(seed));
}
