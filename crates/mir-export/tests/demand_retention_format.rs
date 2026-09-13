#[path = "../src/demand_retention_format.rs"]
mod format;

#[test]
fn header_matches_pinned_rustc_frame() {
    let version = "1.100.0-nightly (cea272fa3 2026-09-07)";
    let bytes = format::header(version).unwrap();
    assert_eq!(&bytes[..6], b"RSIC\0\0");
    assert_eq!(bytes[6] as usize, version.len());
    assert_eq!(&bytes[7..], version.as_bytes());
}

#[test]
fn version_length_is_bytes_and_is_bounded_like_rustc() {
    assert_eq!(format::header("é").unwrap(), b"RSIC\0\0\x02\xc3\xa9");
    assert_eq!(format::header(&"x".repeat(255)).unwrap()[6], 255);
    assert!(format::header(&"x".repeat(256)).is_err());
}

#[test]
fn sparse_cache_directory_does_not_replace_stock_directory() {
    let original = std::path::Path::new("target/guest incremental");
    let sparse = format::incremental_directory(original);
    assert_eq!(sparse.parent(), Some(original));
    assert_eq!(sparse.file_name().unwrap(), format::NAMESPACE);
    assert_ne!(original, sparse);
    assert_eq!(format::incremental_directory(original), sparse);
}
