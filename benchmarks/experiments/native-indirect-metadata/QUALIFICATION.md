# Qualification before timing

Retain initial focus01's11 passing checks, focus02's test-fixture compilation
failure (zero tests executed), and focus03's11 passing expanded checks. The
expanded fixtures explicitly warm callees before capacity/fault checks and
exercise two calls in a single profiled invocation. All repeated executions
use fresh guest state. The implementation did not change between these focuses.

Full tool qualification expects541 workspace checks/profile (428 bytecode,
113 exporter),10 ignored diagnostics, followed by an immutable VM installation.
Retain the adopted exporter/wrapper from35df4077; the prototype changes no MIR
lowering or bytecode artifact format. No default indirect-call activation.

The new --jit-indirect-calls option requires resumable JIT calls, is forwarded
by the launcher, appears in timing metadata and is fixed for each PreparedJit.
Qualification must exercise it explicitly; old modes stay covered independently.
Fresh/prepared suite selection and strict type/borrow failures must still hold.

For original saved profiles, compare complete logical per-PC counts with the
adopted engine, exact results, guest memory and entropy. Native relocation is
permitted only for CallIndirect. Prove the new transitions actually execute,
reconstruct each published operation map and retain code-size/decline accounting.
Do not claim byte-identical native code for an enabled transition experiment.

Only after these checks use the declared40-command changed-source primary
screen, with no relaxed gates or completed-candidate retiming. Full project
histories and parser guards are conditional on a passing primary. Keep the
compiler/descriptor-I/O peer source outside this prototype; merge integration
requires an additional correctness qualification before main runtime adoption.
