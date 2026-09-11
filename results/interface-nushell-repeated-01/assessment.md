# Fifteen Nushell API-edit cycles

Generalizing `Type::list` from `Type` to `impl Into<Type>` passed all fourteen
original type-relation tests through fifteen cycles. Each cycle included the
API edit, an original-source anchor and the original wrong-relation control.
All 135 primary commands and 45 independent checks completed. Source was
restored and all ten recorded script/case hashes matched. The verifier
reconstructed source states and mode order and checked 90 paired artifacts;
each mode occupied each edit position five times.

| Edited command | Median wall | Median CPU |
| --- | ---: | ---: |
| Native root O0/incremental | 12.689 s | 37.008 s |
| Original b2 JIT | 5.504 s | 8.398 s |
| Experimental 78e60cdd JIT | 5.500 s | 8.416 s |

The median within-edit candidate/baseline ratio is **1.0112370245 wall** and
**1.0040872751 CPU**, increases of 1.12% and 0.41%. Ratios of unpaired medians
answer a different question. The median paired wall difference is +0.0558 s,
with a range from −0.6519 to +0.6710 s. These small changes on a shared host
are descriptive, not a significance claim. All samples are retained.

Candidate Cargo time has a 5.418 s median, versus 0.01161 s guest execution.
The independently timed Cargo-check control has a 4.433 s wall median and
7.612 s CPU median. It is a separate cache history, not a strict lower bound;
subtracting it does not isolate exporter overhead. The native/custom gap
includes compiler/build, linking and execution differences. Native used 18
jobs and default libtest concurrency; custom builds used four jobs and std-MIR.
Cold excludes toolchain/dependency fetching and std-MIR setup; OS caches were
not cleared. No whole-suite or best-native claim follows.

Corresponding baseline/candidate artifacts match in every command, and the
generic-edit artifact matches across all fifteen cycles. **Original-source and
wrong-edit artifacts differ between cycle zero and the fourteen later cycles**,
despite identical source and selected tests. The earlier qualification matches
34 of 90 artifacts and differs from 56. These differences remain unresolved;
passing the selected tests does not prove general cross-history equivalence.
The raw artifacts and both hash histories are preserved in the verification.

Together with [pgrust](../interface-pgrust-repeated-01/assessment.md), the two
interface experiments verify 360 commands, 30 edited pairs and 180 artifacts.
Their costs are reported separately. Each repeats one API edit fifteen times;
neither replaces the original five-body-edit, three-cycle corpus. The two
one-cycle qualifications stay outside these totals. Both original token gates
remain failed and the new runtime stays disabled by default.

[Complete samples and stages](summary.json) · [Verification](verification.json)
