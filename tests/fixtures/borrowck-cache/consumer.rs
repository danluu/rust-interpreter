use borrowck_dependency::Convert;

#[inline(never)]
fn unchanged(value: u32) -> u32 {
    let values = [value, value + 1];
    let borrowed = &values;
    borrowed.iter().copied().sum()
}

fn checked_word() -> u32 {
    borrowck_dependency::value()
}

fn main() {
    let bytes = [0u8; borrowck_dependency::WIDTH];
    println!("{}:{}:{}:{}:{}", checked_word(), 41u32.to_word(), bytes.len(),
             borrowck_dependency::macro_value!(), unchanged(2));
}
