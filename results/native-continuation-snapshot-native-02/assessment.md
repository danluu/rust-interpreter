# Native continuation and snapshot qualification passes

All 349 bytecode controls pass in debug and release, with eleven diagnostic
tests ignored per profile. The snapshot control compares every byte and canary
for 401 lengths, sixteen source alignments and nine overlap/disjoint offsets:
57,744 native attempts per profile. It verifies v8-v15 lanes, live call scratch
registers, all preserved general registers and the stack pointer.

Existing controls retain nested native/VM transitions, TLS, fault order, exact
budgets, code-capacity refusal, logical profiles and full operation-map
reconstruction. Dirty spare descriptors now contain a nonzero stale continuation
sentinel, requiring native push to overwrite it. The two comparison tests from
the failed first run validate actual resume-table targets before comparing
caller/PC identities across differently sized generated code.

Production source remains the statically qualified 1d687905 implementation;
only that test comparison changed. Two commands took 63.72 seconds. Closure
verifies 225 frozen bindings and eight retained log/oracle artifacts. Original
project qualification and changed-source timing remain pending. Nothing is
adopted from these correctness results.
