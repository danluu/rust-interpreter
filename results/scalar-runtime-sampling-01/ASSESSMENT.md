# Fresh samples of the qualified private-transfer VM

Both original token tests finish successfully under ordinary OS entropy. Nine
attribution/ownership controls pass. The source-bound run executes the installed
private-transfer VM with persistent registers, resumable and scalar Calls, with
instruction profiling disabled. All generated self PCs join the same process's
reconstructed schema-2 operation map; none remain unassigned.

| Captured self samples | Token block | Exhaustive token |
|---|---:|---:|
| All threads | 2,116 | 1,947 |
| Generated code | 1,814 | 1,480 |
| Copy operations | 487 | 290 |
| General/scalar Call transition spans | 337 | 349 |
| Return transition spans | 114 | 146 |
| Load operations | 262 | 116 |
| Private scalar bodies | 57 | 123 |
| Known post-execution diagnostics | 167 | 211 |

These are disjoint self-PC counts within partial, perturbed three-second
sampling windows. They are not elapsed-time proportions of the full command.
Host samples can include setup, allocator work and diagnostic reconstruction.
The retained bound-entropy profiles supply only static original operation names
and native region boundaries; no dynamic count equality is claimed across the
different entropy sources or observation scopes. Scalar spans identify whole
functions, not individual original operations.

The earlier scalar-body micro-optimizations address a small observed category
in these windows. Ordinary Copy and Call spans are the next useful places to
inspect. Eight-byte copies account for 287 block samples, but their spans include
address/value handling as well as the actual load/store. Reconstruct those
subparts before choosing a new runtime change. Do not infer that all 487 Copy
samples are removable or repeat an already-failed general address-check change.

This diagnostic changes no guest/runtime implementation and establishes no
speedup. The private-transfer candidate remains parked after its failed primary.
Any new candidate retains strict checking and the original edited-source
primary/full gates. The closure verifies 246 input bindings and 56 retained
artifact bindings, including terminal ownership, exact commands and sample/code
hashes.
