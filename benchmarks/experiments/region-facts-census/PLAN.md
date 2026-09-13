# Known facts at native-region boundaries

The checked-address screen did not establish a useful gain and remains parked.
Before another emitter change, count lost whole-function facts on the exact
three saved adopted profiles. No guest execution or timing comparison is needed.

Use typed bytecode, not formatted opcode strings, for all transfer semantics.
Start entry registers unknown, merge only identical facts from every reachable
predecessor, retain all branch successors, and iterate loops to a fixed point.
Known Local/Imm definitions and the existing bounded unsigned local-add/constant
binary rules can establish facts. All other register outputs invalidate them;
value/overflow aliases retain the interpreter's assignment order. Unknown
initial values, skipped definitions, conflicting joins and exhausted analysis
limits must never become proof of an address. Memory writes do not redefine
register values; calls' explicit register effects still require review.

Compare these facts with the same local/constant rules restarted at each saved
native interval. Count positive fixed-size Load/Store and both Copy addresses,
with separate read/write and Copy counts. Existing in-frame proofs stay excluded.
Only a whole-function Local extent fully inside the active frame is eligible.
This first census reports memory-address opportunities only. Broader constant
operand traffic remains unmeasured; these counts are not proven hardware loads,
emitted savings or elapsed time.
Do not equate opcode cost samples with address-validation time.

Bound CFG edges, register operands, stored facts, function work, total work and
report size. Profile/artifact shape and interval counts must match exactly.
Any analysis decline is explicit and contributes no opportunities. Test loops,
joins, skipped initialization, output aliases, clobbers, calls, offset overflow,
Copy endpoints, malformed profiles and exhausted bounds before real censuses.

Extend the existing offline address-census executable with an explicit option;
its existing invocation remains unchanged. No emitter, VM dispatch, cache or
guest checking behavior changes. A later runtime implementation would still
need to prove that each entry path has the analyzed register/frame state,
including direct host entry and resumable calls; this census does not grant
permission to seed arbitrary native entries with whole-function facts.

Serialize tests, compilation and three offline censuses under the shared lock,
45-second admission, two Cargo workers and an 8 GiB floor. Preserve current
source/tool/profile hashes and other sessions. Select an implementation only
after the census shows a meaningful opportunity; do not reopen the failed
checked-address timing campaign.
