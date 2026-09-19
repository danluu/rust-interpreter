const HOST_DEBUG_ASSERTIONS: bool = profile_host_fixture::host_debug_assertions!();

pub fn selected_value() -> u32 { 7 }

#[test]
fn host_and_target_checks_remain_enabled() {
    assert!(HOST_DEBUG_ASSERTIONS);
    assert!(cfg!(debug_assertions));
    assert_eq!(selected_value(), 7);
}
