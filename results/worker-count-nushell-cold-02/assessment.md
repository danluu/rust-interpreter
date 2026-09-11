# Second fixed worker cold history

All twelve commands (nine primary and three independent Cargo checks), six
executed custom artifacts, six wrapper traces and eleven frozen inputs verify.
The fourteen original tests and wrong-edit controls retain their assertions;
the pinned source is restored exactly. Corresponding modes produce identical
bytecode. Both custom modes use tool78 with matched ordinary JIT/inlining;
only Cargo workers differ, four versus eighteen.

| Original-source cold command | Wall seconds | Child CPU seconds |
| --- | ---: | ---: |
| Native, 18 workers | 42.872 | 280.526 |
| Custom baseline, 4 workers | 63.796 | 186.549 |
| Custom candidate, 18 workers | 31.333 | 232.158 |

Candidate/baseline ratios are **0.4911347530 wall** (50.89% lower) and
**1.2444871670 child CPU** (24.45% higher). Initial order was candidate,
baseline, native. These are this history's observations, not a six-history
estimate. Installation, downloads and prebuilt std-MIR setup are excluded;
OS caches and unrelated workloads were not controlled. Child CPU is not
instruction count, energy or a causal explanation of the increase.

The [prefix assessment](../worker-count-cold-decision-through-02/summary.json)
requires continuing the fixed histories. Four observations remain, so both
mathematical lower bounds are zero. Warm guards still pass. No early acceptance,
threshold change, worker default change or conditional held-out stage follows.
The next fixed order is baseline, candidate, native.

Supervisor 2157/controller 2168, verifier 98151/98154, cold assessor 98707/98710
and prefix assessor 99590/99599 all finished successfully. The [preflight](preflight.json)
records 22.993 GiB free at launch and the unchanged eight-GiB command guard.
See [raw-derived observation](cold-observation.json), [verification](verification.json),
[command report](summary.md) and
[fixed protocol](../../benchmarks/experiments/compiler-pipeline/WORKER-COUNT-NEXT.md).
