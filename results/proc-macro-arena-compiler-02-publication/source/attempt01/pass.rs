#![deny(warnings)]
type Value = (u64, &'static str, usize, &'static str);
const A: Value = arena04_macros::exercise!(alpha);
const B: Value = arena04_macros::exercise!(beta);
const C: Value = arena04_macros::exercise!(café);
const D: Value = arena04_macros::exercise!(r#type);
const NESTED: Value = arena04_macros::nest!(nested);
const AGAIN: Value = arena04_macros::exercise!(after_nested);

#[arena04_macros::inspected]
#[derive(arena04_macros::ArenaStamp)]
struct Stamp;

const fn exact(left: &str, right: &str) -> bool {
    let left = left.as_bytes();
    let right = right.as_bytes();
    if left.len() != right.len() { return false; }
    let mut index = 0;
    while index < left.len() {
        if left[index] != right[index] { return false; }
        index += 1;
    }
    true
}

const _: () = {
    let values = [A, B, C, D, NESTED, AGAIN];
    let labels = ["alpha", "beta", "café", "r#type", "nested", "after_nested"];
    let mut index = 0;
    while index < values.len() {
        assert!(values[index].0 == 1337);
        assert!(exact(values[index].1, "arena Ω\n\"\\🙂"));
        assert!(values[index].2 == 8193);
        assert!(exact(values[index].3, labels[index]));
        index += 1;
    }
    assert!(Stamp::ARENA_STAMP == 8193);
};
