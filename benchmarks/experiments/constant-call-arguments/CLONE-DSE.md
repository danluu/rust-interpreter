# Remove proven unobserved writes from specialized bodies

Replay02 passes all34real assertions. Token loses2.60%of logical instructions
but has paired median wall ratio1.00207; folded is0.99678. General arithmetic
folding and more clone admission have not reduced runtime enough to justify an
edited-command screen. Keep these results and the compiler off main.

The next structural candidate removes unobserved frame-memory writes only from
generated clones. This explicitly replaces the earlier blanket retention of all
clone memory writes with a proof for individual operations; original functions,
call ABI, frame size, layout, argument copies and runtime frame clearing remain.

Use the existing certified forward facts to identify exact Local ranges and
constant lengths. Run bounded backward byte liveness over all CFG successors.
Return reads the complete result slot. Calls, unknown memory reads and runtime
builtins conservatively read the entire frame. Known writes kill the overwritten
range before reads are added, preserving overlapping-copy snapshot semantics.
No assumption about Rust pointer provenance, undefined behavior, or heap
pointees participates in the proof.

Remove Store/FillBytes only when the entire destination is proven within the
current live frame and no destination byte is live afterward. Remove Copy or
CopyDynamic only under that same condition and with a fully valid source:
Local within the live frame or non-null immutable program data. Unknown and
out-of-range accesses stay, including reads whose results are unused. Keep all
other operations. Never change static, heap, caller-frame or escaped memory
through an unproven address. Preserve the final register-initialization guard.

Admit at most512operations,4096frame bytes and8192registers per body. Bound total
edges/accesses, forward facts and backward work; decline without partial code
changes on exhaustion. Independently check the final liveness equations before
removal. Keep all branches, remap targets after deletion, and retain original
frames/registers/results. Pure-definition/CFG cleanup is allowed only after the
memory proof and must preserve the no-new-register-clearing requirement.

Differential cases must cover dead clears, valid/invalid copies, partial writes,
overlap, branch joins, loop-carried bytes, unknown aliases, caller observation,
source/destination faults and exhausted bounds. Compare original and transformed
interpreter outcomes and memory peaks, then both native modes and exact budgets
within each artifact. Use the existing saved34-test replay only after full host
qualification. Keep the10%real token edit screen and5%guards unchanged.

Host qualification floor: 4 GiB. Reuse the populated host target with two workers.
No new real-project Cargo cache or cache retirement belongs to this prototype.

Implementation limits:8million forward-fact units and8million backward units
per program, each retaining a2million per-function cap. CFGs admit at most4096
edges and2048cases on one Switch. Eight new differential tests bring the full
workspace expectation to386passed per profile, with one ignored. The old growth
decline test now uses unknown destinations so its writes cannot be discarded by
the new proof. Reports distinguish proposed removal counts from applied changes.
