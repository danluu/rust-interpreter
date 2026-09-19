pub fn profile() -> (&'static str, &'static str) {
    (env!("FIXTURE_BUILD_OPT_LEVEL"), env!("FIXTURE_BUILD_DEBUG"))
}

pub fn checks() -> bool {
    assert!(cfg!(debug_assertions));
    assert!(std::panic::catch_unwind(|| {
        let _ = std::hint::black_box(u8::MAX) + 1;
    }).is_err());
    true
}

