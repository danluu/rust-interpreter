# Immutable private-store runtime candidate

Candidate tool `494c9f013bb5` contains VM `405549cd76bf` with the adopted
`df4006e0` exporter and wrapper unchanged. Its explicit scalar-call path now
selects bounded private external stores and read forwarding. Unknown partial
aliases and private faults replay ordinary execution; strict validation and
the existing limits remain. Main still runs the adopted VM.

All 641 workspace tests pass in debug and release (18 ignored observers per
profile). The complete Python run discovers 429 tests: 407 pass and 22 declared
compiler/native tests skip. Four commands finish in 135.88 seconds of setup.
The closure verifies 503 source/retained bindings and 14 artifacts, including
installed tool identities. The new native controls run in both persistent
register configurations; the earlier census preserves 71 adopted scalar bodies.

No original-project performance comparison ran. Require strict/cache edits,
three original profiles and the fresh changed-source primary before considering
larger project/parser histories or runtime adoption.
