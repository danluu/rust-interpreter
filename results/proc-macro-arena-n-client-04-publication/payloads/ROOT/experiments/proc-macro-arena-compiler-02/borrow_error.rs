pub fn ordinary_borrow_check() {
    let mut value = String::from("owned");
    let held = &value;
    arena04_macros::mutate!(value);
    assert!(!held.is_empty());
}
