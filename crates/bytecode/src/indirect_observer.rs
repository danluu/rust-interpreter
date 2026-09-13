//! Explicit diagnostic entry point; libtest cannot supply the required main thread.
fn main() {
    rust_interp_bytecode::observe_saved_indirect_targets();
}
