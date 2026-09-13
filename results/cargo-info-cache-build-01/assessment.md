# Empty-wrapper Cargo info-cache correctness qualification

The candidate passed all three compiler-info-cache integration tests. The matched stock tool passed both existing tests and failed only the newly added empty-wrapper regression, as expected. This qualifies the behavior change; it is not performance evidence or a claim that the 0.5 s target passed.

The fix makes fingerprinting follow Cargo's existing execution semantics: empty normal/workspace wrappers are not executables. Explicit empty environment values still disable wrappers from Cargo configuration. Nonempty wrapper paths, compiler identities, rustup state, query arguments and query environment remain part of their existing cache validation.

The new test covers empty normal, workspace and both wrapper overrides against nonexistent configured executables. For every case, candidate cold commands miss/update the info cache, warm commands hit without miss/update, and `CARGO_CACHE_RUSTC_INFO=0` continues to disable caching. Existing tests validate ordinary cache reuse, changed compiler paths/timestamps and replacement of real normal/workspace wrappers. The focused integration entry includes the entire upstream info-cache test module, preserving its two existing tests and adding the new regression, plus its ordinary Cargo invocation helper; it does not replace Cargo or compiler work with stubs.

Stock and candidate use Cargo revision `3c0b534756e166d12eb9fd2e1abfe5b42ac6101e`, the same owned source path, pinned nightly-2026-09-08 compiler, release debug level 1, default Cargo features, two build jobs and disabled incremental tool compilation. Dependencies, compiler settings and build/test command lines are shared. The only differing production input is `src/util/rustc.rs`; both states include the same regression and focused test entry. Executables were retained after test builds so dependency-feature unification cannot silently leave a differently built executable outside qualification.

- Stock key: `814a8c7fb449507a5d225e92e70c570d0cc323807dc7adb229a5a80bfd8f5afd`.
- Candidate key: `d5b28c1d96f0f6d5accc338a81e87e07979a11bdf21eb41bf951d02bf0caca2d`.
- Candidate source restored; all commands ran while holding the shared workload lock.

[summary.json](summary.json) records matched tool/source/compiler/profile identities, every exact command receipt, expected/actual test outcomes and fixture paths. [evidence.json.gz](evidence.json.gz) retains exact logs, the original supervisor report, source manifests, patch, harness, relevant Cargo implementation/test snapshots, fixture source/configuration and rustc-info cache files. Every archived member and gzip round trip was verified. Executable binaries, build caches and other compiled artifacts stay in `.work`.

Build/test timings in the exact receipts describe setup and correctness work. Any later performance assessment must compare these two matched local executables; comparing this candidate with a differently built distributed Cargo would confound the source change. Cargo has previous optimization exposure and remains excluded from fresh holdouts.

Repackage saved evidence without executing a workload:

```sh
python3 benchmarks/experiments/cargo-info-cache/assess.py \
  /Users/danluu/dev/rust-interp-cargo-info-cache-20260913/.work/cargo-info-cache-build-01/summary.json --run-id cargo-info-cache-build-01-reproduced
```
