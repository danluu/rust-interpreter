//! Stable entry inputs that are outside the exact owner/resolver input and
//! session option hash. Captured at the real body entry, after normal params.
//! List/set accessors deliberately avoid Features::enabled/TRACK_FEATURE.
use std::collections::BTreeSet;
use rustc_serialize::{Encodable, opaque::mem_encoder::MemEncoder};
use rustc_span::Symbol;
use serde::Serialize;
use crate::LoweringContext;
use super::storage::MAX_RECORD;

const KEY_VERSION: &str = "hir-body-entry-v1";
const MAX_ENTRIES: usize = 4096;
const MAX_TEXT: usize = MAX_RECORD / 8;

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
struct LanguageFeature { name: String, stable_since: Option<String> }

// Named fields bind the association, not just a sequence of eight unlabeled
// arrays. Array order and duplicates are meaningful and never sorted away.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize)]
struct Allowed {
    contracts: Vec<String>, try_trait: Vec<String>, gen_future: Vec<String>,
    pattern_type: Vec<String>, async_gen: Vec<String>, async_iterator: Vec<String>,
    for_await: Vec<String>, async_fn_traits: Vec<String>,
}
impl Allowed {
    fn lists(&self) -> [&[String]; 8] {
        [&self.contracts, &self.try_trait, &self.gen_future, &self.pattern_type,
            &self.async_gen, &self.async_iterator, &self.for_await, &self.async_fn_traits]
    }
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
struct Normalized {
    language: Vec<LanguageFeature>,
    library: Vec<String>,
    allowed: Allowed,
}
impl Normalized {
    fn new(mut language: Vec<LanguageFeature>, mut library: Vec<String>,
        enabled: BTreeSet<String>, allowed: Allowed) -> Option<Self> {
        let allowed_entries = allowed.lists().iter().try_fold(0_usize, |sum, values| sum.checked_add(values.len()))?;
        let entries = language.len().checked_add(library.len())?.checked_add(enabled.len())?
            .checked_add(allowed_entries)?;
        if entries > MAX_ENTRIES { return None; }
        let mut bytes = 0_usize;
        let mut text = |value: &str| -> Option<()> {
            if value.is_empty() { return None; }
            bytes = bytes.checked_add(value.len())?;
            (bytes <= MAX_TEXT).then_some(())
        };
        for feature in &language {
            text(&feature.name)?;
            if let Some(version) = &feature.stable_since { text(version)?; }
        }
        for name in library.iter().chain(enabled.iter()).chain(allowed.lists().into_iter().flatten()) { text(name)?; }
        let union: BTreeSet<_> = language.iter().map(|f| f.name.clone()).chain(library.iter().cloned()).collect();
        if union != enabled { return None; }
        // Only the declarative feature-list order is irrelevant to enablement.
        // Sorting retains categories, stable_since and repeated declarations.
        language.sort(); library.sort();
        Some(Self { language, library, allowed })
    }
    fn bind(&self, base: &[u8]) -> Option<Vec<u8>> {
        let bytes = serde_json::to_vec(self).ok()?;
        if base.len().checked_add(bytes.len())? > MAX_RECORD / 2 { return None; }
        let mut encoder = MemEncoder::new();
        KEY_VERSION.encode(&mut encoder); base.encode(&mut encoder); bytes.encode(&mut encoder);
        let key = encoder.finish();
        (key.len() <= MAX_RECORD / 2).then_some(key)
    }
}
fn names(symbols: &[Symbol]) -> Vec<String> {
    symbols.iter().map(|symbol| symbol.as_str().to_owned()).collect()
}

pub(super) fn bind(lctx: &LoweringContext<'_, '_>, base: &[u8]) -> Option<Vec<u8>> {
    // tcx.features() is the ordinary tracked query. The accessors below do not
    // invoke boolean feature getters, which would add feature-use side effects.
    let features = lctx.tcx.features();
    if features.enabled_lang_features().len() > MAX_ENTRIES
        || features.enabled_lib_features().len() > MAX_ENTRIES
        || features.enabled_features().len() > MAX_ENTRIES { return None; }
    let language = features.enabled_lang_features().iter().map(|f| LanguageFeature {
        name: f.gate_name.as_str().to_owned(), stable_since: f.stable_since.map(|s| s.as_str().to_owned()),
    }).collect();
    let library = features.enabled_lib_features().iter().map(|f| f.gate_name.as_str().to_owned()).collect();
    let enabled: BTreeSet<_> = features.enabled_features_iter_stable_order()
        .map(|(symbol, _)| symbol.as_str().to_owned()).collect();
    // Stable declarations produce the names; cardinality plus membership
    // independently proves equality with the actual enabled set. No hash-set
    // iteration or boolean feature getter (and thus no TRACK_FEATURE) occurs.
    if enabled.len() != features.enabled_features().len()
        || features.enabled_features_iter_stable_order()
            .any(|(symbol, _)| !features.enabled_features().contains(&symbol)) { return None; }
    let allowed = Allowed {
        contracts: names(&lctx.allow_contracts), try_trait: names(&lctx.allow_try_trait),
        gen_future: names(&lctx.allow_gen_future), pattern_type: names(&lctx.allow_pattern_type),
        async_gen: names(&lctx.allow_async_gen), async_iterator: names(&lctx.allow_async_iterator),
        for_await: names(&lctx.allow_for_await), async_fn_traits: names(&lctx.allow_async_fn_traits),
    };
    Normalized::new(language, library, enabled, allowed)?.bind(base)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn language(name: &str, stable: Option<&str>) -> LanguageFeature {
        LanguageFeature { name: name.into(), stable_since: stable.map(str::to_owned) }
    }
    fn normalize(lang: Vec<LanguageFeature>, lib: Vec<&str>, allowed: Allowed) -> Normalized {
        let library: Vec<String> = lib.into_iter().map(str::to_owned).collect();
        let enabled = lang.iter().map(|f| f.name.clone()).chain(library.iter().cloned()).collect();
        Normalized::new(lang, library, enabled, allowed).unwrap()
    }
    #[test]
    fn feature_order_normalizes_but_category_duplicates_and_version_bind() {
        let a = normalize(vec![language("b", None), language("a", Some("1.0"))], vec!["z", "y"], Allowed::default());
        let b = normalize(vec![language("a", Some("1.0")), language("b", None)], vec!["y", "z"], Allowed::default());
        assert_eq!(a.bind(b"owner"), b.bind(b"owner"));
        let changed_category = normalize(vec![language("a", Some("1.0"))], vec!["b", "y", "z"], Allowed::default());
        assert_ne!(a.bind(b"owner"), changed_category.bind(b"owner"));
        let duplicated = normalize(vec![language("a", Some("1.0")), language("b", None), language("b", None)], vec!["y", "z"], Allowed::default());
        assert_ne!(a.bind(b"owner"), duplicated.bind(b"owner"));
        let stable = normalize(vec![language("a", Some("1.1")), language("b", None)], vec!["y", "z"], Allowed::default());
        assert_ne!(a.bind(b"owner"), stable.bind(b"owner"));
        let duplicate_lib = normalize(b.language.clone(), vec!["y", "z", "z"], Allowed::default());
        assert_ne!(b.bind(b"owner"), duplicate_lib.bind(b"owner"));
    }
    #[test]
    fn allowed_array_order_duplicates_and_field_association_bind() {
        let mut allowed = Allowed::default(); allowed.gen_future = vec!["one".into(), "two".into()];
        let original = normalize(vec![], vec![], allowed.clone());
        allowed.gen_future.reverse();
        assert_ne!(original.bind(b"owner"), normalize(vec![], vec![], allowed.clone()).bind(b"owner"));
        allowed.gen_future = vec!["one".into(), "two".into(), "two".into()];
        assert_ne!(original.bind(b"owner"), normalize(vec![], vec![], allowed).bind(b"owner"));
        let mut moved = Allowed::default(); moved.async_iterator = vec!["one".into(), "two".into()];
        assert_ne!(original.bind(b"owner"), normalize(vec![], vec![], moved).bind(b"owner"));
    }
    #[test]
    fn feature_union_mismatch_and_invalid_budget_reject() {
        for enabled in [BTreeSet::new(), BTreeSet::from(["feature".into(), "unknown".into()])] {
            assert!(Normalized::new(vec![language("feature", None)], vec![], enabled, Allowed::default()).is_none());
        }
        assert!(Normalized::new(vec![language("", None)], vec![], BTreeSet::from([String::new()]), Allowed::default()).is_none());
        let long = "a".repeat(MAX_TEXT + 1);
        assert!(Normalized::new(vec![language(&long, None)], vec![], BTreeSet::from([long]), Allowed::default()).is_none());
    }
    #[test]
    fn base_input_and_entry_presence_are_part_of_final_key() {
        let entry = normalize(vec![], vec![], Allowed::default());
        let first = entry.bind(b"owner-a").unwrap();
        assert_ne!(first.as_slice(), b"owner-a");
        assert_ne!(first, entry.bind(b"owner-b").unwrap());
        assert!(entry.bind(&vec![0; MAX_RECORD / 2]).is_none());
    }
}
