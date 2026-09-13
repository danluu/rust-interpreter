#[deny(unconditional_panic)]
fn qualification_uncalled_constant_panic() -> u32 {
    let zero = 0;
    1 / zero
}
