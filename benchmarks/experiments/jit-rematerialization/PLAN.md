# Reconstruct immutable values across native regions

Fresh token execution samples locate most work in generated code. Region-local
facts currently disappear at branches and calls; even an unchanged immediate or
frame-relative address can consume a persistent pair or a register-array slot.
Test a function-wide proof on `experiment/jit-rematerialization-20260912`, based
on e2b515b. This does not include the parked scalar ABI, fixed clears, budget
register, guarded arguments, whole-call expansion, or persistent exporter cache.

For resumable execution with persistent registers, accept only registers whose
every definition is the same immediate or Local offset and which are not live
at function entry. Existing bounded full-CFG liveness establishes that every
reachable read follows a definition. Any other writer or inconsistent definition
disqualifies the register. Bound the new table, prioritize values used across
regions, and conservatively retain the old behavior when analysis declines.
Use exact full-width values and the current frame base. Exclude accepted values
from persistent-pair competition. Before any resumable interpreter continuation,
materialize live values into the original register array, including caller values
before native calls that may return through the interpreter. Faults remain
terminal. Instruction charging, profiles, ABI, guest memory and frame limits,
initial zeros and alias behavior stay unchanged.

Qualify the proof with conflicting definitions, initial reads, unreachable
blocks, loops, high halves and address values. Differential runtime cases must
exercise branches, interpreter exits, nested calls, code-capacity declines and
every small instruction budget, plus deterministic generated valid programs.
Run workspace tests in debug and release and retain raw failure receipts.

Then use one six-pair token runtime screen with the already-qualified two
entropy tapes and identical saved bytecode; require at least 10% median wall
improvement and no CPU regression to justify a complete-command experiment.
This is an early rejection gate, not adoption evidence. Do not retime a failed
candidate. If it passes, run one fresh five-edit paired token/native/check
workflow: require at least 8% complete-command wall improvement and CPU ratio
at most 1.02. Preserve wrong edits and byte-for-byte artifact comparisons.
Only passing screens justify broad original-assertion corpus guards, folded
anchor comparison (at most 3% regression), and fresh 15-pair token confirmation
with the same 8% wall/1.02 CPU gate. Report cold separately. Reject any silent
JIT decline growth as an explanation for a claimed gain.

Use owned installed 7e4ae256 as the runtime control and byte-identical retained
exporter/wrapper binaries. Serialize builds and execution under the shared lock,
wait at most 45 seconds, keep the 8 GiB running floor, and use two build workers.
Keep compact results in Git, raw records in `.work`, and good changes on main.
