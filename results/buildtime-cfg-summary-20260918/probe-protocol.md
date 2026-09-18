# Executed retained-program CFG diagnostic

The measured source is `probe.rs`. It compares `optimize_control_flow` with `optimize_control_flow_summary` using the same candidate library and exact retained artifact. It does not execute guest code.

The original execution directory was `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/cfg-pass-probe`. Its standalone Cargo package selected the bytecode path dependency, bincode 1.3.3 and sha2 0.10.9, preserving all selected registry blocks from the root lockfile. The controller used pinned Cargo/rustc/rustdoc with `build --release --locked --offline --jobs 2`, a private target and no incremental compilation.

Two initial invocations wrote new artifacts whose bytes were compared exactly. Then two warmup pairs and 20 measured pairs alternated detailed/summary order. Measured processes omitted output-file arguments. Every sample required the same function/operation counts and output digest. The parent retained real child exits and wait4 CPU/RSS. Input/tool/source proofs were checked before and after. Resource admission and the complete sample rows are recorded in summary.json.

All output bytes equal the retained input. Full-export timing remains inconclusive; see README.md for the decision and limits.
