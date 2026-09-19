# Qualify against the unchanged adopted VM on the current host

The historical replay stopped after one successful candidate assertion run:
15,849,531,264 logical instructions versus historical 15,849,531,246. Saved
profiles differ only in fre_target_features::macos::{detect_aarch64,integer}.
The current host answers the FAMINMAX and LUT queries successfully with zero;
the historical control took two query-error branches. This is a hypothesis
about the source of the drift until the unchanged adopted binary agrees.

Preserve all original files and the failed supervisor. Freeze their hashes.
Run the unchanged adopted binary on case 0 and compare every logical PC with
the already retained new-VM run. Only after exact agreement, execute one adopted
and one candidate run for each remaining original case, using the original
artifacts, catalogs and diagnostic entropy tapes. Five fresh commands total;
no candidate case-0 replay. Require original assertions, exact current A/B PC
counts, memory and entropy, complete native maps and all frozen hashes. Preserve
and report historical differences; permit them only in the two detection
functions with the exact 18-instruction total delta (or zero if absent).
No timing, sysctl interposition, entropy in benchmarks or relaxed runtime gate.

Record read-only host query status/value/length before and after. Independently
close both the retained failure and the five-command qualification, revalidating
all source/input/output hashes and semantic comparisons. Shared lock45s,
12GiB admission/8GiB children. No new build or compiler changes.
