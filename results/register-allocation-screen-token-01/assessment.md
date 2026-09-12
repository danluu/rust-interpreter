Register lifetime allocation is parked off main. The fixed screen regressed
paired complete-command wall time by **4.64%** and child-tree CPU by **4.70%**.
It failed the required 10% wall improvement/no-CPU-regression gate. No guard
workloads, broader retention run or retiming follow.

All 32 native/check/custom commands passed their expected outcomes on the twelve
token tests. The deliberately incorrect edit failed the same original assertions.
All eight source states also passed the independent exact artifact verifier:
candidate bytes equal applying the typed allocation to the control artifact,
including every non-register field. All sources and sixteen executed snapshots,
catalogs, selections, raw commands and verifier reports are preserved.

Median edited commands were native 3.068 s, retained 8.147 s, candidate 8.500 s,
and check 0.666 s. The allocation pass cost about 0.198 s per edited export.
Median paired Cargo and VM-stage increases were 0.191 s and 0.183 s,
respectively. Stage medians do not establish causal attribution and need not add
to the median command delta. Both custom modes executed exactly the same VM.

The prototype passed 352 Rust tests/profile, generated differential executions,
eighteen native/checked/VM fixture commands, and exact working-memory threshold
checks. The large static slot reduction did not predict an end-to-end gain.

Source remains on `experiment/register-lifetimes-20260912`; main retains only
the previously qualified offline census and the experiment evidence. The next
direction investigates constant call arguments and simplification, preserving
runtime checks and the parked status of this allocation.
