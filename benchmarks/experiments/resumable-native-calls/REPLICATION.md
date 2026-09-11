# One unchanged-tool replication

The completed `resumable-bulk-e2e-01` run passes folded at −19.51% but narrowly
fails token: ratio 0.8004639304 versus the original maximum 0.8. CPU improves
about 20.5% on both. This cutoff is a decision criterion, not a significance
test; the 0.0464 percentage-point miss does not measure the uncertainty.

Before another runtime change, run exactly one additional original three-cycle
folded/token corpus as `resumable-bulk-e2e-02`. Use source `001065a`, installed
tool `78e60cdd`, original b2 baseline and resumable+persistent flags. All tool,
artifact, workload, assertion, wrong-edit, source-restoration, native-control,
limits, cache-history and CPU requirements remain unchanged. Use fresh task
cache namespaces as the existing driver does. Never disrupt unrelated work.

Evaluate the same −10% folded/−20% token numerical gates with CPU improving.
Retain the first failure and both independent run decisions. Report all 30
edited pairs per workload across the two runs, per-run and per-edit wall/CPU
variation, and the paired versus cross-history artifact distinction. Any pooled
summary is descriptive only; it is not a newly invented retention gate. A
second-run pass does not retroactively turn the first run into a pass. If the
classifications disagree, state that the 20% classification is unstable.
Do not run repeated attempts until one passes.

Use this replication to decide whether further performance work or broader
experimental compatibility qualification is more useful. Do not retain by
rounding, dropping slower edits or treating profile percentages as savings.
The seven held-out workflows and native/TLS/fre execution qualification remain
required before a production retention decision. Their tracked preparation is
in [BROADER-QUALIFICATION.md](BROADER-QUALIFICATION.md); the new full native
validator driver still needs its first actual selected-tool execution.
