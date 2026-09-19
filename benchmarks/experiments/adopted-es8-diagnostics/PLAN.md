# Current ES8 execution diagnosis

The independently closed adopted-es8-edit-01 history gives1.516x custom/native
wall and1.833x CPU over five real edits. Median custom execution is1.237s out
of2.077s end-to-end; the integration exporter alone is not the dominant stage.

Reuse the exact restored original bytecode/catalog from custom row31 and the
immutable adopted df4006 VM. Run one bounded logical operation profile per
original test, then one ordinary-entropy native sample per test (up to3s,
one repetition). Four new original-test executions, no compiler/source edit,
runtime candidate, foreign guest backend, timing comparison or adoption.

Keep strict-checking and original-assertion provenance from the closed edit
history. Profiles use explicit scalar/resumable/persistent options,100B steps,
150k allocations and existing default memory/frame/code limits. Validate original
test selections, zero JIT declines, successful unit results, exact sum of
per-PC counts and same-process schema2 code reconstruction. Profile counts are
descriptive, not compared across ordinary-entropy executions. Samples use the
profile only for static function/operation identity and native boundary checks.

Reuse the closed vmmap-label-compatibility-01 compatibility evidence and the
subsequent composed-native-sampler-protocol-01 qualification:11 attribution
controls, two early CLI rejections and14 retained-map replays, with exact current
sampler/decoder sources. The later option recording leaves indirect calls off
for these diagnostics. Each sample captures only the fresh child it creates,
verifying PID/parent/cwd/start identity before read-only vmmap/sample. All guests
finish naturally. No signals, peer process control or retry after a missed window.
Save every child result before validation; failed/partial evidence is retained.
Any reporting repair must consume retained evidence without repeating guests.

Initial12GiB and before-child8GiB;45s shared-lock admission, single guest at a
time. Profile commands hold the lock; the existing sampler acquires its own lock.
Freeze inputs through independent closure. Recompute logical derivations and
verify every terminal/log/artifact/code/map hash independently. Do not interpret
instrumented execution time or partial sample shares as expected speedups.
