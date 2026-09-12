The first source-level qualification stopped while compiling its host artifact
inspector. This pinned Cargo build produced an rlib containing only a metadata
stub; the diagnostic command supplied that rlib without the corresponding full
rmeta. No guest export or execution ran. Source/logs and terminal process
receipts are preserved. Revision 2 supplies both files and freezes metadata and
proc-macro dependencies too. The compiler/runtime source is unchanged.

Rust documents this split in its [embed-metadata option](https://doc.rust-lang.org/nightly/unstable-book/compiler-flags/embed-metadata.html).
