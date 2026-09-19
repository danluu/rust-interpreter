# Defer unselected installers in the standalone std CLI

Source-only proposal against immutable baseline `050a7d2a1e9677bc467a49fdba7a2ab485566e97` in `/Users/danluu/dev/rust-interp-std-readmission-publication-20260918`. No project import, test, compiler query, benchmark, cache/std preparation, or worktree application has run.

The only production change wraps the existing imports at `scripts/std_mir.py:170–171` in their matching `args.compiler_key is not None` / `args.cargo_key is not None` conditions. The imports stay at the same location, compiler before Cargo. The subsequent custom assignment, options construction, loaders, namespace/readmission call and output remain byte-identical. Unwrapping those two guards restores the entire baseline AST; every other function is unchanged.

Stock standalone `std_mir.py` setup avoids importing unused custom compiler and custom Cargo installers. Compiler-only selection skips the direct Cargo-installer import. Both-selected ordering is preserved. Cargo itself retains its normal custom-compiler dependencies when actually selected. An empty explicit key remains selected and reaches its original rejecting loader. No validation, cache identity or readmission check is removed.

This scope is standalone CLI setup/readmission orchestration. The interpreter launcher calls `checked_std_mir` directly and does not execute `std_mir.main`, so this proposal does not claim another gain on that published launcher path. `toolchain_lookup` still imports `tempfile` on stock lookup; nothing in this patch changes tempfile, cached lookup behavior or the parked C8 work. No observed speedup or full std-build/export/runtime/holdout improvement is claimed.

The new `tests/test_std_mir_selection.py` has eight focused methods:

- Stock selection reaches setup with no installer import/call and preserves the printed receipt.
- Compiler-only selection preserves namespace and source-path options without the Cargo installer.
- Cargo-only selection preserves Cargo/fetch dispatch without calling the compiler loader.
- Both selections preserve compiler-then-Cargo imports, loader order and chosen tool objects.
- Invalid partition selection fails before imports/loading/setup.
- An explicitly empty compiler key reaches its loader; rejection happens after both requested imports and before Cargo loading/setup.
- An explicitly empty Cargo key reaches its loader and does not fall back.
- A source-path policy rejected by setup propagates unchanged without loading unselected installers.

Tests use a real private temporary root and small corpus file, fake installer modules/loaders, and a mocked `checked_std_mir` boundary. They assert forwarded arguments, error/dispatch order and exact output, while Popen/run are patched to fail any accidental child launch. They never populate `.work`, build std metadata or load a real installed compiler. The module import hook deliberately detects requests for unused installers even when other suites already populated `sys.modules`; it is a unit behavior check, not a cold-process performance measurement.

Keep the existing six `test_custom_compiler_launcher.py` and seven `test_custom_cargo.py` methods unchanged for downstream custom-tool, namespace, environment and readmission coverage. The proposed candidate qualification is those thirteen plus the eight new methods (21 total). The new import-boundary assertions intentionally fail on the old unconditional-import implementation; do not run all eight against baseline while expecting every result to pass. No qualification result is asserted here.

Any later fixed timing should exercise actual standalone `main` setup in fresh processes, with exact mocked-boundary scope if std preparation is stubbed, and include an ordinary selected-tool regression guard. A bare module-import screen misses the changed imports because they live inside main. Numerical gates, selected fixture panel and runtime measurement bindings remain for root to choose before data. No timing controller is included.

`source-bindings.json` records both production copies, the absent baseline/new candidate test file, exact method names and AST proof. `candidate.patch` contains only those two paths. The concise source lead is `W/new-build-time-leads/stock-std-cli-optional-imports.md`, SHA256 `6b2f42c326d2ac8e4cc61e5692a433952e0164b994eb5d338fe91bb6e4005054`.
