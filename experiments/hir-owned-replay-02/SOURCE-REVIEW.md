# Independent source review

Root and runtime_installation reviewed the owned replay implementation and six
equivalence fixtures. No semantic blocker was found in this source review.
Compilation and actual compiler tests remain outstanding.

The removed validation receives the same tree and immutable Current as the
retained validation. The intervening current_state check does not mutate context,
intern values, invoke queries, or change either input. Conversion produces owned
values before CheckedTree::into_tree moves its raw tree; CheckedTree has no custom
Drop implementation. The old prepare API still revalidates cross-Current inputs.
ReadyHit construction, fallback, commit trace, recapture, expected-tree comparison,
and poststate checks remain unchanged.

The new tests compare actual legacy and owned preparation, including a separately
valid journal whose order disagrees with the tree. They cover the existing
block/integer fixture shape and do not establish full expression coverage.

Root separately reconstructed every patch hunk against the recorded compiler
source, checked all 26 resulting file digests, and recomputed the 25-file acyclic
source identity: 8946102708c589586d3be0169b409e4465b43c2d2498ab61aa26c125ecf22099.
The full patch digest is a05d49fe06fcb924632ca4c4d9483a9e960ed31f66165a0dbef96b127a42e2cb.
This was an in-memory source check, with no checkout mutation, compiler execution,
benchmark, or performance claim.
