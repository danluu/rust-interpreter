include!(concat!(env!("OUT_DIR"), "/generated.rs"));

const MACRO_VALUE: u64 = ibs_fixture_macros::fixture_value!(11);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generated_file_matches_current_helper_and_inputs() {
        let input: u64 = include_str!("../input.txt").trim().parse().unwrap();
        let seed: u64 = std::env::var("IBS_FIXTURE_SEED")
            .unwrap_or_else(|_| "3".into()).parse().unwrap();
        assert_eq!(GENERATED_INPUT, input);
        assert_eq!(GENERATED_SEED, seed);
        assert_eq!(GENERATED_VALUE, ibs_fixture_helper::transform(input, seed));
    }

    #[test]
    fn cargo_directives_reach_compilation() {
        let input: u64 = include_str!("../input.txt").trim().parse().unwrap();
        let seed: u64 = std::env::var("IBS_FIXTURE_SEED")
            .unwrap_or_else(|_| "3".into()).parse().unwrap();
        let mode = if cfg!(feature = "native-shared-helper") { "native-shared" } else { "script-only" };
        assert_eq!(cfg!(ibs_seed_even), seed % 2 == 0);
        assert_eq!(env!("IBS_GENERATED_CONTEXT"), format!("input={input};seed={seed};mode={mode}"));
    }

    #[test]
    fn proc_macro_uses_its_actual_dependency_mode() {
        let expected = if cfg!(feature = "native-shared-helper") {
            ibs_fixture_helper::transform(11, 0)
        } else {
            11
        };
        assert_eq!(MACRO_VALUE, expected);
    }
}
