# Original profiles pass; primary timing is next

Three candidate profiles pass against three retained profiles of adopted tool
df4006e0. The control's exact binaries, profile/artifact/catalog/entropy hashes,
observer sources and closed evidence verify. The three observer and seven
launcher controls are reused, not counted as new executions. Candidate tool
cb47107b9d64 uses the same exporter/wrapper and enables scalar Calls in common
with the adopted control.

| Original test | Adopted scalar Calls | Candidate scalar Calls | Native bytes, adopted → candidate |
| --- | ---: | ---: | ---: |
| token block boundaries | 11,227,102 | 18,954,465 | 11,952,720 → 11,994,268 |
| exhaustive token bytes | 16,298,574 | 16,399,347 | 14,508,196 → 14,551,816 |
| folded prefilter | 1,585,153 | 1,585,159 | 1,978,352 → 1,978,944 |

Every original assertion passes. Per-PC logical instruction counts, memory
peaks, and entropy requests/bytes are identical. Candidate native execution
absorbs 24 / 24 / 1 formerly interpreted instructions respectively; the exact
logical total remains unchanged. All complete same-process native maps validate,
with zero declined JIT functions and unchanged liveness-decline counts. Absolute
machine bytes across processes are not compared because Call targets relocate.
The closure verifies 65 frozen inputs and 24 retained artifacts.

The block test moves another 7,727,363 Calls and 518,482,022 logical instructions
into scalar native bodies. This measures execution coverage, not latency.
Profiles use checked entropy replay for equality; the forthcoming 40-command
changed-source primary uses normal OS entropy and fresh baseline/A/A/candidate
commands. Main remains on the adopted runtime until all performance guards pass.
