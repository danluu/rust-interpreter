# Region-level linear propagation remains low coverage

Sixteen controls pass; all original single-operation candidates remain included.
Both source-qualified captures reconcile exactly. Grouping all spans within each
native region finds 45,430 / 54,667 static dead definitions, but only 7 / 13 of
1,561 / 1,231 saved self-PC samples. No regions decline and no sampled candidate
status is ambiguous. No runtime implementation is justified by this result.

This recognizer conservatively treats every conditional branch as requiring every
register. One remaining diagnostic will propagate liveness through actual branch
successors, comparing preservation of every return register with the explicit C
return contract. Keep external region entries and unknown calls conservative.
The test is an opportunity census, not executable optimization or timing.

Closure verifies 75 source/artifact bindings and full details. No compiler,
guest or executable-code publication ran. [Summary](summary.json), [closure](closure.json).
