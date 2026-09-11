# Third fixed worker cold history

All twelve commands (nine primary, three independent Cargo checks), six
executed custom artifacts, six wrapper traces and eleven frozen inputs verify.
The fourteen original tests and wrong-edit controls retain their assertions;
the pinned source is restored exactly. Corresponding modes produce identical
bytecode. Both use immutable tool78 with matched ordinary JIT and leaf inlining;
only the custom Cargo worker count differs.

| Original-source cold command | Wall seconds | Child CPU seconds |
| --- | ---: | ---: |
| Native, 18 workers | 44.379 | 284.633 |
| Custom baseline, 4 workers | 67.678 | 204.702 |
| Custom candidate, 18 workers | 35.016 | 266.197 |

Candidate/baseline ratios are **0.5173956507 wall** (48.26% lower) and
**1.3004076381 child CPU** (30.04% higher). Order was baseline, candidate,
native. These are this history's observations, not the planned six-history
median. Installation/downloads/prebuilt std-MIR setup are excluded. OS caches
and unrelated workloads were not controlled; CPU time is not instruction count
or energy use.

The [three-history assessment](../worker-count-cold-decision-through-03/summary.json)
reverifies both warm primaries and all three cold histories. With three histories
remaining, the exact minimum possible six-sample medians are 0.2455673765 wall
and 0.6222435835 CPU. Neither proves failure, so continue the fixed fourth order:
native, candidate, baseline. No early acceptance, added trials, CPU-threshold
waiver, worker default change or held-out eligibility follows.

Supervisor 19719/controller 19729, verifier 11048/11058, cold assessor 14149/14156
and prefix assessor 15552/15563 all finished successfully. The [preflight](preflight.json)
records 23.672 GiB free and the unchanged eight-GiB command guard. See
[raw-derived observation](cold-observation.json), [verification](verification.json),
[command report](summary.md) and
[fixed protocol](../../benchmarks/experiments/compiler-pipeline/WORKER-COUNT-NEXT.md).
