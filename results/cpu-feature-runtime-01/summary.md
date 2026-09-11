# CPU-query VM: regression screen on identical bytecode

The candidate adds CPU-query support. These existing artifacts contain no new CPU-query instructions, so the comparison measures effects on the old interpreter/JIT paths. Each case has six alternating prior/current pairs in fresh processes. All96 commands return the expected result; all non-timing instruction, memory and JIT statistics are identical across the two VMs.

| Engine / artifact | Prior median (s) | Current median (s) | Median paired change (ms) | Current wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 1.725888 | 1.747736 | +13.443 | 2/6 |
| jit:word64-inline8 | 1.129723 | 1.146904 | +2.454 | 2/6 |
| jit:sha1-inline8 | 0.473762 | 0.467874 | -3.256 | 5/6 |
| jit:word64-default-leaf-inline | 1.520054 | 1.525151 | +8.364 | 2/6 |
| jit:word64-inline8-leaf-inline | 0.948884 | 0.947772 | -1.046 | 3/6 |
| jit:sha1-inline8-leaf-inline | 0.403844 | 0.406055 | +2.922 | 1/6 |
| interpreter:word64-default | 14.584500 | 14.548927 | +83.444 | 2/6 |
| interpreter:sha1-inline8 | 4.768794 | 4.808353 | +74.344 | 2/6 |

Every sample and shared-host load observation is retained. These runtime-only results exclude Cargo, checking, export and launcher work. They do not establish a production-edit speedup; full commands remain the decision metric. The new coverage and its separate native controls are recorded in the capability report.

[Correctness gates](../cpu-feature-default-validation-01.json), [303 fresh passing original tests](../cpu-feature-capability-01/summary.md). Raw measurements: `.work/cpu-feature-runtime-01/`.
