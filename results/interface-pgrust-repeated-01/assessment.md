# Fifteen pgrust API-edit cycles

Generalizing `hash_bytes` to borrowed `AsRef<[u8]> + ?Sized` inputs passed all
four original tests through fifteen cycles. Each cycle included the real API
edit, an original-source anchor and the original wrong-multiplier control.
All 135 primary commands and 45 independent checks completed. The verifier
reconstructed every source state and mode order, checked 90 paired artifacts,
and confirmed each mode occupied every edit position five times. Source was
restored and all recorded script/case hashes matched.

| Edited command | Median wall | Median CPU |
| --- | ---: | ---: |
| Native root O0/incremental | 0.663 s | 0.635 s |
| Original b2 JIT | 0.495 s | 0.487 s |
| Experimental 78e60cdd JIT | 0.491 s | 0.481 s |

The median within-edit candidate/baseline ratio is **0.9886177072 wall** and
**0.9882573381 CPU**, about 1.14% and 1.17% lower respectively. The independent
checking median is 0.386 s. These small differences are descriptive, not a
significance claim or evidence that native calls materially help this workload.
The native/custom gap includes checking, code generation, linking and execution;
it is not solely an execution-backend comparison.

All source-state artifacts also matched across the fifteen cycles and the
earlier one-cycle qualification. This observation is specific to this workload;
it does not resolve the separate fre cache-history layout differences.
The qualification pair stays separate from these fifteen measured pairs.

This design repeats **one API edit fifteen times**, unlike the original corpus's
five distinct body edits repeated three times. It adds interface-change evidence
without replacing those workloads or their failed primary token gates. Native
used 18 jobs/default libtest concurrency, custom builds four jobs; all assertions,
budgets and guest options are preserved. Cold commands exclude toolchain and
dependency fetching; OS caches were not cleared.

[Complete samples and per-edit spread](summary.json) · [Verification](verification.json)
