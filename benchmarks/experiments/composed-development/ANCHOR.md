# Prospective original-selection anchor

Run `workflows.py --case anchor` with the corrected build and its fresh cache,
execution and serial-suite proofs. Build03 is held after the frame-padding audit.
Compare the combined candidate against immutable tool9637b0ac and a duplicate
of that same anchor in separate caches. The anchor identity and original three
token tests come from `results/aggregate-relocation-e2e-01-token-phrase/summary.json`.
Keep their order, five production edits, MIR settings, instruction/allocation
limits and build-script optimization setting. Check every installed binary
against its recorded build hashes before timing.

Both custom modes use the original repeated `--entry` interface: one ordinary
batch with a shared guest execution, stopping at the first assertion failure.
Neither side uses the prepared or isolated runner, a test filter, nor parallel
suite workers. Successful execution must return exactly `0`; the wrong edit
must reach a guest assertion, not merely exit with a compiler or infrastructure
error. Ordinary native libtest still runs all three tests and must reproduce
their exact outcomes. The old batch cannot report separate test outcomes after
the first failure; record this limitation without fabricating per-test results.

Use the same six-mode schedule, separate caches, three cycles, fifteen edited
pairs, fifteen same-session A/A pairs, final compiled restoration and two Cargo
workers as the selected-suite comparison. Ordinary default-thread libtest is
the primary native control; repository settings and an explicit line-tables
control are both retained. The older native timings used different worker and
profile settings, so compare to newly measured controls, not to old medians.
No unchanged build is a latency sample. No replay library is injected.

Predeclare a material8% median paired complete-command wall improvement, with
CPU ratio at most1+max(1%, observed A/A CPU envelope). The descriptive per-edit
median A/A envelopes must be at most4% wall and3% CPU. These are not confidence
intervals. Keep all pairs; do not repeat a completed failed screen to seek a
pass. Stop and preserve evidence on a command or source-validation failure.
Require9GiB at admission and3GiB before each child. Never control unrelated
workloads to create an idle machine or obtain the benchmark lock.

This tests the cumulative compiler/runtime implementation on the original
selection. It does not measure prepared execution or the benefit of parallel
tests. Report the selected-suite comparison separately, without multiplying
ratios or adding gains from incompatible workloads. Adoption still needs the
folded/pgrust and broader held-out guards.
