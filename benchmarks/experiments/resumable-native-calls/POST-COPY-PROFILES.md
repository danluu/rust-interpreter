# Choose the next change from the current emitted code

Finish the fixed seven-case comparison and amended aggregate first. Preserve any
regression rather than rerunning to seek a pass. The current runtime remains
source `aa2f6ea`, tool `0e94d6d8`, with resumable calls and persistent registers.
Its matched-frontend comparison improved token paired wall time 15.14%; the
combined original-baseline comparison improved folded 21.82% and token 33.09%.
Both compute workflows still take longer than the recorded native control.

The previous tool78 profiles no longer describe the current boundary mix:
native copies reduced token native entries from about 22.4 million to 2.65
million. Do not infer the next optimization from the old percentages alone.

Use the executed candidate cycle-zero artifacts from the completed
`resumable-copy-original-e2e-01` folded and token histories. Bind their hashes
against recorded snapshots before launch. Use the immutable current VM and
the existing qualified `sample_owned_vm.py` driver, three fresh processes per
workload, three-second token samples and one-second folded samples, with emitted
code dumps. Keep original assertions, instruction/allocation limits, runtime
flags and naturally finishing owned processes. The first diagnostic IDs are
`resumable-copy-token-sample-01` and `resumable-copy-folded-sample-01`.

Verify the original test result, VM statistics, binary/artifact/source hashes,
same-process mappings and each emitted-code range. Preserve short or incomplete
captures explicitly; do not lengthen the workload or invent unavailable samples.
Attribute sampled PCs to exact emitted instructions and report unmapped or
unclassified samples. Native transfer loops may need explicit diagnostic
classification; qualify any analyzer change against prior reports before using
it to select runtime work. No guest emitter change is part of profiling.

Collect separate full-run transition counts with the existing driver where
needed to explain a sampled bottleneck. Sampling and instrumented counts are
diagnostics, not speed measurements. Reconcile counts with the VM's exact totals
and keep their overhead out of end-to-end results. Serialize all diagnostics
under the benchmark lock after the primary histories are terminal.

Choose one substantial measured cost for the next experiment. A proposed frame
initialization change needs a proof of read-before-write and alias behavior;
old narrow argument-only, unused-local and private-array censuses remain parked.
A proposed check or ABI change must preserve full values, initialization, guest
fault order, exact instruction budgets and fallback continuation state. State
the next meaningful end-to-end target and regression controls before changing
the runtime. No project/function-name specialization or external guest backend.

In parallel with planning, keep the separate compatibility direction explicit:
an unfiltered suite attempt should identify real missing behavior. Current
body replay does not qualify libtest, unwinding, threads or general OS/FFI.
Success-returning shims and skipped cleanup are not compatibility fixes.
