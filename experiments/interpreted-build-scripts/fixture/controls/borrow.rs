fn qualification_uncalled_borrow_error() {
    let mut value = 1_u32;
    let first = &mut value;
    let second = &mut value;
    *first += 1;
    *second += 1;
}
