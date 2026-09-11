# Scratch-frame reuse: actual comparison repeated after calibration

The repeated comparison wins **12/20** complete edited commands. The original run won **10/20**; keeping both gives **22/40**. All selected original tests pass and all modes reject the wrong production edit. Both source checkouts are restored.

The same archived cd9 baseline and 67b3 scratch-frame candidate are used in both runs. VM binaries are identical; exporters differ. Explicit retained-candidate selection leaves the current guarded working-tree engine unchanged. All executed artifact hashes and binary identities were rechecked.

| Workflow | Run | Command wins | Paired command change (ms) | Execution wins | Paired execution change (ms) | Paired Cargo change (ms) |
|---|---|---:|---:|---:|---:|---:|
| fre-folded-literal-trie | [original](../e2e-paired-fre-folded-literal-trie-temporary-frame-01/summary.md) | 2/5 | +3.129 | 5/5 | -53.823 | +42.644 |
| fre-folded-literal-trie | [repeat](../e2e-paired-fre-folded-literal-trie-temporary-frame-recheck-01/summary.md) | 4/5 | -113.373 | 5/5 | -19.042 | -85.440 |
| fre-word64 | [original](../e2e-paired-fre-word64-temporary-frame-01/summary.md) | 4/5 | -58.335 | 4/5 | -5.644 | -40.504 |
| fre-word64 | [repeat](../e2e-paired-fre-word64-temporary-frame-recheck-01/summary.md) | 2/5 | +16.693 | 5/5 | -5.174 | +20.404 |
| fre-word64-inline8 | [original](../e2e-paired-fre-word64-inline8-temporary-frame-01/summary.md) | 0/5 | +61.252 | 3/5 | -4.806 | +63.946 |
| fre-word64-inline8 | [repeat](../e2e-paired-fre-word64-inline8-temporary-frame-recheck-01/summary.md) | 4/5 | -17.953 | 4/5 | -6.151 | -4.689 |
| pgrust-sha1-inline8 | [original](../e2e-paired-pgrust-sha1-inline8-temporary-frame-01/summary.md) | 4/5 | -18.803 | 4/5 | -2.034 | -9.831 |
| pgrust-sha1-inline8 | [repeat](../e2e-paired-pgrust-sha1-inline8-temporary-frame-recheck-01/summary.md) | 2/5 | +0.685 | 3/5 | -0.279 | +3.229 |

| Workflow | Combined command wins | Combined paired command change (ms) | Combined execution wins | Combined paired execution change (ms) |
|---|---:|---:|---:|---:|
| fre-folded-literal-trie | 6/10 | -44.678 | 10/10 | -31.674 |
| fre-word64 | 6/10 | -17.342 | 9/10 | -5.409 |
| fre-word64-inline8 | 4/10 | +13.422 | 7/10 | -5.479 |
| pgrust-sha1-inline8 | 6/10 | -12.330 | 7/10 | -1.207 |

Negative changes favor scratch-frame reuse. Per-stage medians need not add to the complete-command median. Repeating the same five edit states gives another run of these workflows, not ten independent workload examples or a confidence interval. Both run blocks and every individual pair remain in summary.json.

The prior identical-tool calibration motivated this recheck; it does not excuse regressions or supply a correction to subtract from these timings. Complete commands include Cargo, strict checking, export, launch, JIT construction and execution. Cold/setup costs and fresh native controls are retained in each linked report. Downloads, tool bootstrap and shared standard-library MIR setup are outside the command timers.

Scratch reuse remains an archived experiment while this evidence is reviewed. The fresh 389-case fre survey and broader project corpus were not run for it. This report does not claim whole-application support or universal speedup.

[Identical-tool calibration](../identical-tools-aa-e2e-01/summary.md), [original decision](../paired-temporary-frame-compute-01/summary.md), [CPU evidence](../folded-trie-guarded-cpu-sample-01/summary.md).
