use super::*;
use wire::*;

const SOURCE: &str = "fn f(){}";

fn span(lo: u32, hi: u32) -> SourceSpan { SourceSpan::Relative { lo, hi } }
fn tree() -> OwnerTree {
    OwnerTree {
        ident: Ident { text: "f".into(), span: span(3, 4) }, span: span(0, 8), vis_span: span(0, 0),
        signature_span: span(0, 6), generics_span: SourceSpan::Dummy, where_span: SourceSpan::Dummy,
        lifetime_elision_allowed: false, input_types: vec![], output_type: ReturnType::Default(span(6, 6)),
        params: vec![], local_id_limit: 3,
        value: Expr { node: Node { local: 2, span: span(6, 8) }, kind: ExprKind::Block(Block {
            node: Node { local: 1, span: span(6, 8) }, statements: vec![], tail: None,
        }) },
    }
}

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!("rustc-hir-owner-test-{}-{}", std::process::id(),
            NEXT_TEMP.fetch_add(1, Ordering::Relaxed)));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for Temp { fn drop(&mut self) { fs::remove_dir_all(&self.0).unwrap(); } }

#[test]
fn rejects_duplicate_ids_and_out_of_source_spans() {
    assert!(validate::check(tree(), SOURCE).is_some());
    let mut duplicate = tree();
    duplicate.value.node.local = 1;
    assert!(validate::check(duplicate, SOURCE).is_none());
    let mut outside = tree();
    outside.signature_span = span(0, 9);
    assert!(validate::check(outside, SOURCE).is_none());
    let mut sparse = tree();
    sparse.local_id_limit = 4;
    assert!(validate::check(sparse, SOURCE).is_none());
}

#[test]
fn rejects_bad_keys_unknown_fields_truncation_and_checksums() {
    let temp = Temp::new();
    let path = temp.0.join("record");
    assert!(read(&path, &[1], SOURCE).is_none());
    write(&path, &[1], tree()).unwrap();
    assert!(read(&path, &[1], SOURCE).is_some());
    assert!(read(&path, &[2], SOURCE).is_none());
    let bytes = fs::read(&path).unwrap();
    fs::write(&path, &bytes[..bytes.len() / 2]).unwrap();
    assert!(read(&path, &[1], SOURCE).is_none());
    let mut value: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    value["extra"] = true.into();
    fs::write(&path, serde_json::to_vec(&value).unwrap()).unwrap();
    assert!(read(&path, &[1], SOURCE).is_none());
    value.as_object_mut().unwrap().remove("extra");
    value["checksum"] = "wrong".into();
    fs::write(&path, serde_json::to_vec(&value).unwrap()).unwrap();
    assert!(read(&path, &[1], SOURCE).is_none());
}

#[test]
fn rejects_semantically_invalid_payload_even_with_matching_checksum() {
    let temp = Temp::new();
    let path = temp.0.join("record");
    let mut bad = tree();
    bad.value.node.local = 1;
    write(&path, &[1], bad).unwrap();
    assert!(read(&path, &[1], SOURCE).is_none());
    let mut bad = tree();
    bad.ident.span = span(1, 2);
    // A byte position inside a Unicode scalar cannot become a diagnostic span.
    assert!(validate::check(bad, "λxxxxxx").is_none());
}

#[test]
fn publication_does_not_modify_hardlinked_previous_session() {
    let temp = Temp::new();
    let path = temp.0.join("record");
    let previous = temp.0.join("previous");
    write(&path, &[1], tree()).unwrap();
    let bytes = fs::read(&path).unwrap();
    fs::hard_link(&path, &previous).unwrap();
    write(&path, &[2], tree()).unwrap();
    assert_eq!(fs::read(&previous).unwrap(), bytes);
    assert!(read(&previous, &[1], SOURCE).is_some());
    assert!(read(&path, &[2], SOURCE).is_some());
}

#[test]
fn malformed_or_unwritable_storage_is_only_a_cache_miss() {
    let temp = Temp::new();
    assert!(read(&temp.0, &[1], SOURCE).is_none());
    let destination = temp.0.join("destination");
    fs::create_dir(&destination).unwrap();
    assert!(write(&destination, &[1], tree()).is_none());
    assert_eq!(fs::read_dir(&temp.0).unwrap().count(), 1);
    let oversized = temp.0.join("oversized");
    fs::write(&oversized, vec![0; MAX_RECORD as usize + 1]).unwrap();
    assert!(read(&oversized, &[1], SOURCE).is_none());
    #[cfg(unix)]
    {
        let regular = temp.0.join("regular");
        let symlink = temp.0.join("symlink");
        write(&regular, &[1], tree()).unwrap();
        std::os::unix::fs::symlink(&regular, &symlink).unwrap();
        assert!(read(&symlink, &[1], SOURCE).is_none());
    }
}
