# Original profiles retain all logical behavior

All three original tests pass with exact adopted-control assertions, per-PC
logical counts, instruction counts, peak memory, entropy calls/bytes and native
code/map reconstruction. Three candidate executions reuse the three SHA-bound
adopted profiles; unchanged observation/launcher controls are reused explicitly.

| Original test | Adopted scalar Calls | Aggregate scalar Calls |
| --- | ---: | ---: |
| token block | 11,227,102 | 11,263,838 |
| token exhaustive | 16,298,574 | 21,432,046 |
| folded | 1,585,153 | 2,648,800 |

The new path covers5,133,472 additional Calls in exhaustive and1,063,647 in folded.
These counts establish coverage, not a speedup. Recorded entropy is used only
for this identity check; the prospective changed-source primary uses ordinary
entropy. All65 frozen inputs and24 profile/code artifacts are closed.
[Summary](summary.json), [closure](closure.json).
