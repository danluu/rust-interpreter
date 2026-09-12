# Independent-workload confirmation

Use the exact screened baseline and deferred-binary candidate binaries with
five additional public saved-artifact cases, six alternating paired repeats
after one warmup pair for each engine. The selected cases and expected outputs
are in confirmation.json and were selected before any timings.

Require expected outputs, instruction counts and peak guest memory unchanged.
Require no >5% wall or CPU regression that also exceeds5ms absolute median
difference in any additional case for either interpreter or retained JIT.
Retain every sample. Interpret all timing summaries descriptively.
No code or benchmark-case-specific tuning after examining these timings.
