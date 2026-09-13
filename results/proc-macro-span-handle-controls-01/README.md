# Standalone proc-macro span-handle controls

The exact candidate handle.rs compiled with public rustc cea272fa3 and passed all four container tests: ordered-store equivalence with repeated values and counter gaps; cross-store/stale-handle rejection; zero-counter rejection; and overflow rejection. The pinned sibling fxhash.rs was unchanged. The harness imports the standard macros at crate root so its cfg_select invocation remains the original source.

Compilation used Rust2024, opt-level0, debug assertions and overflow checks enabled, and two backend jobs. The test binary ran once with one test thread. Compiler/source snapshots and hashes, exact argv/environment, raw compiler/test output and process receipts are retained. These are container invariants, not a bridge integration test or performance result. No full compiler build or microbenchmark ran.

The first supervisor failed after the four tests had passed: its output parser omitted libtest's ` - should panic` suffix. That exact failed receipt is retained. Separate validation02 checked the saved four outcomes and all original source/compiler hashes under the canonical lock. It launched no compiler or tests and did not replace the failed receipt. Both completed supervisors are archived. The test binary hash was collected during continued validation; the binary itself is excluded.

Every archive member and source was checked after packaging. Original evidence and the private test binary remain unchanged.

The initial verified archive included the generated dSYM companion. Compact publication excludes its three files, retaining their hashes and the initial packaging receipts. The original archive remains privately preserved.
