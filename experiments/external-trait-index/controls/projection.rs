#[cfg(test)]
mod external_trait_item_index_tests {
    use super::{BindingKey, IdentKey, Namespace, external_trait_item_names};
    use rustc_span::hygiene::{LocalExpnId, Transparency};
    use rustc_span::{Ident, Symbol, SyntaxContext, DUMMY_SP, kw};

    #[test]
    fn projection_keeps_namespaces_and_ignores_hygiene_and_disambiguators() {
        rustc_span::create_default_session_globals_then(|| {
            let name = Symbol::intern("member");
            let missing = Symbol::intern("missing");
            let marked = SyntaxContext::root().apply_mark(
                LocalExpnId::fresh_empty().to_expn_id(), Transparency::Opaque);
            let mut keys = Vec::new();
            for ns in [Namespace::TypeNS, Namespace::ValueNS, Namespace::MacroNS] {
                keys.push(BindingKey::new(IdentKey::with_root_ctxt(name), ns));
                keys.push(BindingKey::new(IdentKey::new(Ident::new(name, DUMMY_SP.with_ctxt(marked))), ns));
            }
            for disambiguator in [1, 2, u32::MAX] {
                keys.push(BindingKey::new_disambiguated(
                    IdentKey::with_root_ctxt(kw::Underscore), Namespace::ValueNS,
                    || disambiguator));
            }
            assert_ne!(keys[0], keys[1]);
            assert_ne!(keys[6], keys[7]);
            let indexed = external_trait_item_names(keys.iter());
            assert_eq!(indexed.len(), 4);
            for name in [name, missing, kw::Underscore] {
                for ns in [Namespace::TypeNS, Namespace::ValueNS, Namespace::MacroNS] {
                    assert_eq!(indexed.contains(&(name, ns)),
                        keys.iter().any(|key| key.ident.name == name && key.ns == ns));
                }
            }
            // Index construction accepts keys only: no best declaration or
            // NameResolution value can accidentally filter this projection.
            assert!(external_trait_item_names([].iter()).is_empty());
        });
    }
}
