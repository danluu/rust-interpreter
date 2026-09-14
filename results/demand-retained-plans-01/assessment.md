# Bounded immutable plan ownership qualifies

Source eb525ec1 passes all 352 bytecode controls in each profile (13 ignored),
including exact-limit admission, one-byte-short refusal, duplicate/invalid ID
handling, release accounting and unchanged eager code from a refused plan.
Both adopted captures reconstruct and independently reassemble exactly:
20,033/23,406 regions and 11,313,812/13,757,056 bytes. Four commands take
64.352296 seconds. The closure verifies 305 source/input bindings and ten outputs.

Retained fill and call-slot hints are sorted vectors with exact-key lookups.
The plan pool permits at most 16 MiB of charged owned payload, including its
index vector and inline header. It never replaces an admitted plan on refusal;
the caller receives the untouched analysis for the existing eager path. The pool
is qualified but not connected to preparation or execution yet.

This charge is not a process-memory limit: allocator rounding, transient full
analysis, code/tables/pending edges and cfg(test) oracle buffers are outside it.
Publication metadata still needs bounded ownership and transaction qualification.
No changed-source command runs and no end-to-end improvement is established.
