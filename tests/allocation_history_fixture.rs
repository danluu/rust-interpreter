mod api {
    #[inline(never)]
    pub fn identity(value: u64) -> u64 { value }
}

// Keep all workload code and assertions below this marker unchanged across edits.
#[inline(never)]
fn first(value: u64) -> u64 {
    if value == 42 { panic!("Expected OneOf"); }
    value
}

#[inline(never)]
fn depends_on_api(value: u64) -> u64 {
    let result = api::identity(value);
    if result == 42 { panic!("Expected OneOf"); }
    result
}

#[inline(never)]
fn third(value: u64) -> u64 {
    if value == 42 { panic!("Expected OneOf"); }
    value
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let a = first(seed);
    let b = depends_on_api(seed ^ 1);
    let c = third(seed ^ 2);
    assert_eq!(a, seed);
    assert_eq!(b, seed ^ 1);
    assert_eq!(c, seed ^ 2);
    a.wrapping_add(b).wrapping_add(c)
}

fn main() {
    let seed = std::env::args().nth(1).unwrap().parse().unwrap();
    println!("{}", rust_interp_entry(seed));
}
