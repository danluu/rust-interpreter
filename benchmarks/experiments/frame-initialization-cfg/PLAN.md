# Bounded CFG and callee-effect initialization census

Start from the closed native-call cost census on branch
`experiment/frame-initialization-cfg-20260913`. This is a standalone typed
analyzer. Do not change runtime clearing, the compiler, bytecode or benchmark
workloads. Its Rust dependency is the exact current source; saved adopted
artifacts and sampled code keep their own identities. Main also has newer
descriptor/getcwd support, which stays outside this source boundary.

Prove from function PC zero that every read of its allocated frame is preceded
by an argument copy or write. Carry initialized-byte and exact Local-register
facts across CFG edges; intersect at joins and iterate loops with a bounded
worklist. Unreachable code has no execution from this entry. Pointer facts are
killed through the complete register-write visitor. Initially, only declared
argument bytes are initialized; result padding and the allocated byte of a
zero-sized frame remain obligations. Unknown writes establish no facts; a Copy
must read before it writes. Unknown reads/effects require the complete frame
already initialized. Decline resource limits conservatively.

A separate typed callee summary admits only memory accesses inside its own
frame and explicit argument/result transfers to similarly confined direct
callees. Acyclic dependencies are processed before callers; recursive effect
cycles stay unproved. No name-based special cases or effect inference from
Debug strings. At an admitted Call, validate/read all argument source ranges
before treating the returned result as a write. Unknown/indirect callees keep
the conservative rule. The summary does not claim its own frame can skip
clearing: that is the separate initialization proof.

Call-site eligibility additionally requires current caller-local argument hints
for every nonempty source. A future emitter must guard the actual addresses
before changing clearing; hints alone are insufficient at arbitrary native
entries. Alignment padding and register initialization remain unchanged. This
first diagnostic is only a coverage bound, not a runtime safety certificate.

Test CFG joins/backedges, skipped writes, pointer kills, partial/overlapping
reads and copies, zero-sized frames, result padding, confined nested calls,
unknown/recursive effects and analysis limits. Include a small independent
path/byte oracle. Then join exact typed Call IDs to the two saved protocol maps
and clearing sample PCs. Reconcile total calls and samples before assessing
scope. Run no guest workloads or timing screen at this stage.

Use the shared lock with 45-second admission, two Cargo workers, 16 GiB before
building, 12 GiB for analysis and 8 GiB before each child. Use owned artifacts
and record exact sources, build times and terminal outcomes. Preserve the paused
goal, other worktrees and the independent cleaner. No subagents or AWS changes.
