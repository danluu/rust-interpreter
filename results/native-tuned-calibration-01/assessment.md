# Native debug settings: fre calibration inconclusive

All 21 complete Cargo commands and 15 diagnostic executable repeats completed with the expected assertion outcomes. Source was restored, log hashes verified and all processes are terminal. Native uses 18 jobs/default threads and O0/incremental.

Edits 1–3 were the calibration set. Line tables improved median paired command wall time by **7.86%**, below the predeclared **8%** screen; no debuginfo improved it by **5.17%**. No preset was selected. The remaining two edits were retained but cannot retroactively choose a winner. The study is inconclusive for promoting a control.

| Preset | Command | Cargo-reported build | Native suite | Separate binary repeat | CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| repository | 2.031s | 1.10s | 0.60s | 0.595s | 2.523s |
| line-tables-only | 1.908s | 1.10s | 0.47s | 0.460s | 2.344s |
| none | 1.892s | 1.11s | 0.47s | 0.464s | 2.449s |

The table describes all five real edits; selection used only the first three. Medians are separate observations and need not add. Interestingly, Cargo-reported build durations barely changed, while the suite and diagnostic repeat were shorter with reduced debuginfo. This measurement alone does not explain the generated-code difference.

The repeat is a different execution and is never subtracted from the Cargo command. It ran from the workspace directory rather than Cargo’s package directory, using the benchmark environment rather than Cargo’s complete injected test environment; the selected pure-computation tests passed. Future repeats should use the package directory and continue to report their scope separately.

Empty-target initial commands were 6.947s repository, 6.405s line tables and 6.314s no debuginfo. These exclude toolchain/download and OS-cache coldness. No unchanged-build time enters the decision.

Decision: keep the threshold and record the inconclusive result. No repeat of this calibration is scheduled. A large frontend-dominated target remains a separate useful native-control question; fre does not establish that debuginfo tuning is irrelevant there. Preserve this native target for an unfiltered suite measurement. This study compared native presets only, so it does not establish a new custom/native speedup.
