use std::{env, fs, path::Path};

fn main() {
    let source = Path::new("../../../crates/bytecode/src/jit.rs");
    println!("cargo:rerun-if-changed={}", source.display());
    let text = fs::read_to_string(source).unwrap();
    let start = "fn branch(op: &Op) -> bool {";
    let end = "// Generated regions return small continuation indices on success.";
    assert_eq!(text.matches(start).count(), 1);
    assert_eq!(text.matches(end).count(), 1);
    let fragment = &text[text.find(start).unwrap()..text.find(end).unwrap()];
    assert_eq!(fragment.matches("fn supported(").count(), 1);
    assert_eq!(fragment.matches("fn local_fills(").count(), 1);
    // Compile the emitter's exact predicate and local-fill proof. No second
    // opcode support list or parsing of Debug operands participates in eligibility.
    fs::write(Path::new(&env::var_os("OUT_DIR").unwrap()).join("support.rs"), fragment).unwrap();
}
