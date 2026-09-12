//! Resolve canonical definition paths before accepting short-name shorthand.
pub fn resolve<T: Copy>(candidates: &[(String, String, T)], requested: &str) -> Vec<T> {
    let exact: Vec<_> = candidates.iter().filter(|(full, _, _)| full == requested)
        .map(|(_, _, id)| *id).collect();
    if !exact.is_empty() { return exact; }
    candidates.iter().filter(|(_, short, _)| short == requested)
        .map(|(_, _, id)| *id).collect()
}

#[cfg(test)]
mod tests {
    use super::resolve;
    #[test]
    fn root_definition_is_not_ambiguous_with_nested_leaf_names() {
        let names = vec![("test".into(), "test".into(), 1), ("nested::test".into(), "test".into(), 2)];
        assert_eq!(resolve(&names, "test"), vec![1]);
        assert_eq!(resolve(&names, "nested::test"), vec![2]);
    }
    #[test]
    fn short_names_require_unambiguous_candidates() {
        let names = vec![("one::test".into(), "test".into(), 1), ("two::test".into(), "test".into(), 2),
                         ("one::unique".into(), "unique".into(), 3)];
        assert_eq!(resolve(&names, "test"), vec![1, 2]);
        assert_eq!(resolve(&names, "unique"), vec![3]);
        assert!(resolve(&names, "missing").is_empty());
    }
}
