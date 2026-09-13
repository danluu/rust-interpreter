# Native host MIR correctness qualification

The saved first run passed **91 Rust tests and all four real compiler/Cargo histories**, with no skipped tests. This package qualifies the candidate's tested correctness scope; it contains no performance comparison or claim that the 0.5 s target was met.

The policy omits the wrapper-added `-Zalways-encode-mir=yes` only for unselected native host libraries with complete standard-library MIR context, an unambiguous link emission, and no target or response-file arguments. Explicit user flags remain intact. Selected guest export and metadata-only compilation retain their existing policy.

| Retained correctness history | Evidence |
| --- | --- |
| Uncalled type, borrow, constant evaluation and unconditional-panic errors | Candidate, forced full MIR and stock rustc all reject each fixture; the test compares structured diagnostics. All 12 expected failures are retained. |
| Generic, inline and const native consumers | Candidate, forced full MIR and stock rustc produce 39, 43, then 39 across dependency-body edit and restoration; all nine native executions pass. |
| Metadata-only non-generic dependency | Candidate and forced full MIR produce identical selected guest bytecode; both VM executions return 23. |
| Cargo shared host/guest dependency, build script and proc macro | Original/edit/restored states pass in all three modes; six selected guest VM runs and three stock Cargo tests pass. Build-script and proc-macro values follow the real dependency edit. Candidate and forced full MIR bytecode match in each state, differ after the edit, then reproduce the original bytes on restoration. |

The Cargo fixture records separate native-host and target-side dependency invocations, procedural-macro compilation and the selected test artifact. The fixture's selected assertions remain unchanged during edits. The source-state ledger records values 3, 7, 3, and the retained source and final bytecode hashes match restoration. Earlier bytecode snapshots were not retained separately: their hashes and equality/restoration checks come from the saved passing test and ledger. Final bytecode and build-script outputs were rechecked while packaging.

This preserves ordinary native checking within the tested scope. Metadata-only calls remain forced because omitting full MIR there can change diagnostics for otherwise uncalled constant-panic bodies. Internal `rustc_force_inline` diagnostics in otherwise uninstantiated bodies can be forced only by legacy full MIR; that remains a known limitation of the native-host scope. These results do **not** establish universal diagnostic-byte identity for every unstable compiler feature.

Source revision: `16f4c33b91d1ae3432638e428e17fadcfb9db91f`. Installed tool key: `f005d3f31f03ac673208b7aac66110489d371603e4a7336de34db0da46121fab`. The compiler is pinned nightly-2026-09-08, rustc commit `cea272fa356e94bd2ee2cadf376630aa0683867a`, aarch64-apple-darwin, LLVM 23.1.1. The exporter and wrapper were qualified with release debug level 1 (`CARGO_PROFILE_RELEASE_DEBUG=1`) and tool-build incremental compilation disabled. The retained VM was unchanged: all 110 recorded VM source inputs were checked against the candidate source manifest, its current files and the retained VM source manifest. No alternate compiler optimization profile is introduced here.

[summary.json](summary.json) records source, compiler, installed binary, capability, standard-library MIR and test-harness hashes, the three supervisor/child receipts, and compact history outcomes. [evidence.json.gz](evidence.json.gz) retains exact UTF-8 bytes of the build/install records, command logs, stdout/stderr, fixture sources, wrapper traces, source-state ledger and provenance manifests. Every archived member hash and gzip round trip was checked. Compiled outputs and caches remain in `.work`; only their identities are published. Build/test elapsed times in the original receipts are setup/correctness records, not performance samples.

Repackage saved evidence into a fresh directory without executing a workload:

```sh
python3 benchmarks/experiments/strict-warm-build/assess_native_host_mir.py \
  /Users/danluu/dev/rust-interp-host-mir-20260913/.work/host-mir-build-01/summary.json \
  --run-id native-host-mir-build-01-reproduced
```
