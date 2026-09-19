// Exact stock Arena is included unchanged. No reset API or substitute allocator.
#[path = "original_arena.rs"]
mod arena;

#[test]
fn live_disjoint_mutable_strings_survive_shared_growth() {
    let arena = arena::Arena::new();
    let shared = &arena;
    let first = shared.alloc_str("first");
    let second = shared.alloc_str("second");
    first.make_ascii_uppercase();
    second.make_ascii_uppercase();
    let large = shared.alloc_str(&"x".repeat(4096 * 2));
    large.make_ascii_uppercase();
    assert_eq!(first, "FIRST");
    assert_eq!(second, "SECOND");
    first.make_ascii_lowercase();
    second.make_ascii_lowercase();
    assert_eq!(first, "first");
    assert_eq!(second, "second");
    assert!(large.bytes().all(|b| b == b'X'));
}
