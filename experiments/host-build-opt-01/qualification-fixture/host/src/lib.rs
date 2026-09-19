extern crate proc_macro;

#[proc_macro]
pub fn host_observations(_: proc_macro::TokenStream) -> proc_macro::TokenStream {
    assert!(cfg!(debug_assertions));
    assert!(std::panic::catch_unwind(|| {
        let _ = std::hint::black_box(u8::MAX) + 1;
    }).is_err());
    assert!(profile_shared_fixture::checks());
    format!("({:?}, {:?}, {:?}, {:?})",
        env!("FIXTURE_BUILD_OPT_LEVEL"), env!("FIXTURE_BUILD_DEBUG"),
        profile_shared_fixture::profile().0, profile_shared_fixture::profile().1)
        .parse().unwrap()
}

