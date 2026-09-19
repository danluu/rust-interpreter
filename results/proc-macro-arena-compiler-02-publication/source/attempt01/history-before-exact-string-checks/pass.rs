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

const _: () = {
    let values = [A, B, C, D, NESTED, AGAIN];
    let labels = [5, 4, 5, 6, 6, 12];
    let mut index = 0;
    while index < values.len() {
        assert!(values[index].0 == 1337);
        assert!(values[index].1.len() == "arena Ω\n\"\\🙂".len());
        assert!(values[index].2 == 8193);
        assert!(values[index].3.len() == labels[index]);
        index += 1;
    }
    assert!(Stamp::ARENA_STAMP == 8193);
};
