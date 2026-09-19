const HOST: (&str, &str, &str, &str) = profile_host_fixture::host_observations!();

#[test]
fn profile_contract() {
    let level = env!("HOSTQUAL_EXPECTED_LEVEL");
    assert_eq!(HOST.0, level);
    assert_eq!(HOST.2, level);
    assert!(["true", "false"].contains(&HOST.1));
    assert!(["true", "false"].contains(&HOST.3));
    assert_eq!(env!("FIXTURE_BUILD_OPT_LEVEL"), "1");
    assert_eq!(env!("FIXTURE_BUILD_DEBUG"), "true");
    assert_eq!(profile_shared_fixture::profile(), ("1", "true"));
    assert!(profile_shared_fixture::checks());
    assert!(cfg!(debug_assertions));
    assert!(std::panic::catch_unwind(|| {
        let _ = std::hint::black_box(u8::MAX) + 1;
    }).is_err());
}
