# Optional Cargo import startup measurement

The ordinary launcher no longer imports `custom_cargo` unless `--cargo-key` is selected. Mandatory compiler validation and selected-Cargo behavior are unchanged.

At base `5f016241c7795bef75f90c7e2e3db403f0a5c733`, 12 alternating baseline/candidate pairs of fresh Python 3.14.7 processes measured the real CLI through its invalid-tool-key rejection. Each arm had one dependency-bytecode warmup; measured commands used `-B`. Both arms produced the same error and exited before Cargo, cache setup or VM execution. All samples were retained. The shared benchmark lock was held; each child had fresh direct disk and memory admission checks.

Median CPU time changed from 35.479 ms to 34.864 ms; median paired saving was 0.693 ms (12/12 pairs lower). Median wall time changed from 38.172 ms to 37.489 ms; median paired saving was 0.793 ms (11/12 pairs lower). Median peak RSS was unchanged. This is a small startup-component improvement, not a full-build or holdout speedup claim.

All 36 existing tests in `test_interpreter_tools`, `test_custom_cargo`, `test_custom_compiler_launcher`, and `test_interpreter_build_metrics` passed.

`summary.json` retains commands, source hashes, all warmup and measured rows, exact child exits, wall/CPU/RSS, output hashes, admission records, paired differences, and validation provenance. An earlier attempt stopped on its first unmeasured warmup because the harness expected the wrong error prefix; it produced no measured samples and was retained separately.
