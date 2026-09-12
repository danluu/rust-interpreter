# Running the fixed budget-register comparison

`budget_workflows.py` implements the gates already declared in
`BUDGET-REGISTER-NEXT.md`. It does not change their thresholds or samples.
Control is `9637b0ac`, candidate `36656766`; exporter and wrapper hashes match.
The candidate must first pass native, original-artifact, TLS and fre body
qualification. Fre's 382 matched artifact hashes must remain identical.

Run the four cases in this order, each through `scripts/supervise_experiment.py`
with the run ID formed as `budget-register-PHASE-01-CASE`:

1. `--phase aa --case folded-literal-trie`
2. `--phase aa --case token-phrase`
3. `--phase e2e --case folded-literal-trie`
4. `--phase e2e --case token-phrase`

The existing benchmark deliberately rejects identical tools. For A/A only, the
driver stages its exact source and replaces that one guard with an exact-key
requirement for control `9637b0ac` on both sides. All benchmark assertions,
source edits, cache namespaces, scheduling and measurements remain unchanged.
The driver separately binds every case setting and runtime/compiler option.
The original shared harness is unchanged. Source hashes cover the staged file.

The guard was checked for all four control/candidate key combinations: only
control/control is accepted. Changed and duplicated staging anchors are rejected.
All original Python assertion ASTs must match at staging time. The complete A/A
runs remain the actual measurement controls, not a prediction of noise.

Each case requires 63 primary commands, 21 independent checks, 15 edited pairs,
42 exact paired artifacts and source restoration. The A/A wall envelope is the
larger of the absolute median ratio deviation and rank 14 of 15 absolute paired
ratio deviations. All samples remain. It is not a confidence interval.

Token must improve complete-command wall time at least 10%, reduce child CPU,
and exceed its A/A envelope. Folded must stay within 5% wall and CPU regression.
Keep failed performance gates as completed results. Do not rerun valid A/A
controls to narrow their envelope or relax gates after seeing measurements.
All seven held-outs remain required before adoption; this driver covers the
primaries only. Space admission precedes each case and the child keeps the
eight-GiB running floor. External work is never stopped to obtain resources.
