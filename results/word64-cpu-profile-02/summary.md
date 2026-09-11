# Word64 profile after register initialization changes

A two-second diagnostic window sampled 1,548 stacks in the custom JIT running
the same final-edit artifact used in the register-initialization comparison.
The verified, task-owned VM completed all original tests. Profiling ran outside
benchmark measurements; its elapsed time is not a performance result.

Checked memory copying accounts for 313 samples (20.2%): 198 in `Memory::copy`,
94 in its platform `memmove` calls, and 21 in the dynamic call stub. One additional
`memmove` sample belongs to scalar load and is excluded. The VM-loop symbol has
380 leaf samples (24.5%); this includes dispatch and inlined frame/call logic.
`Jit::run` has 138 (8.9%). Short windows do not establish whole-run fractions.

The next bounded experiment replaces common small copies with fixed-size byte
snapshots, preserving overlap, bounds, and read-only checks. First compare the
same artifact on both VM builds, then repeat complete production-edit commands.
Do not infer an end-to-end win from sampling or instruction counts.

The fixed-size snapshot candidate passed bytecode and native differential checks
but lost all five runtime pairs: 3.096 s versus 3.047 s median. An inline hint
with only an early empty-copy return also failed to improve the paired median
(3.051 s versus 3.018 s). Both changes were removed; neither received an
end-to-end qualification. The added overlap/bounds regression tests remain.
[Snapshot experiment](../small-copy-rejected-01.json),
[simpler copy experiment](../copy-inline-inconclusive-01.json).

[Recorded identities and counts](summary.json). Raw ownership checks, memory
map, and full sample remain in `.work/fre-word64-cpu-sample-02`.
