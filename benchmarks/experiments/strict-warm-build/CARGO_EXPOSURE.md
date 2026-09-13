# Cargo prior optimization exposure

Recorded on 2026-09-13 during the strict warm-build investigation. Cargo is
excluded from the fresh holdout pool under the protocol's existing prior-use
rule. This note does not change the frozen screening protocol or the
predetermined rust-analyzer/rustfmt reserve ranking.

The repository already contains a Cargo optimization experiment predating this
campaign:

- [scripts/build_cargo.py](../../../scripts/build_cargo.py) lines 22–40 patch
  Cargo's `crates/cargo-util/src/paths.rs` to call
  `preserve_executable::identical_executables`, and copy the repository helper
  into the Cargo checkout. Lines 47–54 build the patched Cargo binary.
- [compiler/preserve_executable.rs](../../../compiler/preserve_executable.rs)
  implements that executable-publication optimization.
- [Historical benchmarking instructions](../../../docs/history/BENCHMARKING-20260910-before-review.md)
  line 86 explicitly run `python3 scripts/build_cargo.py`.
- [scripts/prepare.py](../../../scripts/prepare.py) line 21 pins Cargo to
  `3c0b534756e166d12eb9fd2e1abfe5b42ac6101e`.

The existing checkout at
`/Users/danluu/dev/rust-interp/.work/sources/cargo` records that revision and
belongs to the separate shared workspace. It is inspected read-only for the
startup investigation; no source mutation, build, test or benchmark is run by
this investigator. Current source inspection is additional exposure, not the
first use of Cargo for optimization in this repository.

The current read-only investigation inspected these Cargo implementation paths:
`src/bin/cargo/main.rs`; `src/context/mod.rs`;
`src/util/{rustc,logger,log_message}.rs`; `src/workspace/{workspace,profiles}.rs`;
`src/compiler/mod.rs`; `src/compiler/job_queue/mod.rs`;
`src/compiler/build_runner/mod.rs`; `src/compiler/build_context/target_info.rs`;
`src/compiler/timings/mod.rs`; and `src/ops/cargo_compile/mod.rs`.
Symbol searches also exposed matching lines elsewhere under Cargo's `src/`
and `doc/` trees. No Cargo implementation file was read before the prior-use
exclusion was identified and the parent explicitly authorized this inspection.
