# First fixed worker cold history

The first of six declared fresh-target histories completed and verifies all
twelve commands (nine primary, three independent Cargo checks), six executed
custom artifacts and six wrapper traces. Both custom modes use identical
installed tool78 and flags, with four/eighteen Cargo workers. All fourteen
original tests and the wrong-edit control retain their assertions. Source
restoration, exact corresponding bytecode, pinned revision and eleven frozen
inputs verify.

| Original-source cold command | Wall seconds | Child CPU seconds |
| --- | ---: | ---: |
| Native, 18 workers | 40.470 | 259.349 |
| Custom baseline, 4 workers | 64.029 | 189.053 |
| Custom candidate, 18 workers | 35.571 | 287.938 |

Candidate/baseline ratios are **0.5555410355 wall** (44.45% lower) and
**1.5230560848 child CPU** (52.31% higher). These are one history's ratios,
not the planned six-history median. Compilation order was native, baseline,
candidate. Downloads, tool installation and prebuilt std-MIR setup are excluded;
OS caches were not cleared and other workloads were not controlled. Child CPU
is not instruction count, energy use or proof of the cause of the increase.

The [prefix decision](../worker-count-cold-decision-through-01/summary.json)
reverifies both warm primaries and this cold history. With only one observation,
neither numerical failure bound can reject every possible completion. Continue
the remaining fixed histories; no early acceptance, worker default change,
extra trials or CPU-threshold waiver. The next order is candidate, baseline,
native. The edit/wrong/revert commands are controls and do not add cold samples.

Supervisor 3180/controller 3183, verifier 88134/88137, cold assessor 88302/88305
and prefix-decision supervisor 88758/88761 all finished successfully. The
[preflight](preflight.json) records 20.651 GiB free before launch. A separately
preserved [correction](preflight-correction.json) fixes a 49-byte transcription
error in the prior-cache reference total; the admission test and command did
not depend on that field and did not change.

See [raw-derived observation](cold-observation.json), [verification](verification.json),
[full command report](summary.md) and
[fixed protocol](../../benchmarks/experiments/compiler-pipeline/WORKER-COUNT-NEXT.md).
