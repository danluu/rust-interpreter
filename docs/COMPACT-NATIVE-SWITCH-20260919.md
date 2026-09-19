# Compact native switch experiment

The new candidate shortens common AArch64 switch comparisons while preserving
the complete 128-bit guest value. It is correctness-qualified and has no new
performance result yet. Its session/runtime parent remains parked after the
unmeasurable full parser gate; the adopted runtime remains `df4006e0`.

The independently closed current-composition census found 116 switch self samples
among 1,514 generated samples in fre's block test and 78 among 1,306 in exhaustive.
All sampled switch tables had cases at most 4095; 84/57 samples were single-zero
tables. This motivated a generic emitter change, with no workload dispatch or
assumption about observed input values. The captures are partial and perturbed;
sample shares cannot predict speedup.

A single zero case ORs both halves and compares the result with zero. Other
nonempty tables whose cases are all at most 4095 test the upper half once and
compare each low half with an immediate. General cases retain the original
two-half comparisons. First-match and duplicate order are unchanged. Excluding
operand loads and the final default successor, a single zero uses four words
instead of seven; a small table uses `2 + 3*n` instead of `7*n` words. These are
static code counts, not timing results. Budget, ABI, profile-PC, fallback,
code-capacity and strict checking contracts remain unchanged.

Runtime source `9bf97808` passed seven focused controls in debug and release,
including local assembler encodings, high-bit values, duplicate cases, backedges,
every instruction-budget boundary and exact template reuse. Full actual-source
qualification `f04edef9` passed 727 Rust tests in each profile (19 ignored),
446 Python tests (22 skipped), 41 diagnostic checks, 11 feature-off session
checks and 35 ordinary template-model checks. It recorded 52 owned session
processes and 108 clients. Setup took 195.40 seconds.

Saved checked parser and fre histories then passed 1,824 and 192 test invocations,
respectively, including deliberately wrong and restored source states. Every
one of 19,206 parser and 14,575 fre cache hits matched fresh current emission.
These were correctness replays, not source-build timings. Their independent
closures are in `results/compact-native-switch-{parser,fre}-replay-01`.

Installation `compact-native-switch-install-01` is closed. Tool key is
`cc1ebf5ef2e1e652a26ee57a1205a916bd989faa617f94d7fcdceb9b53f064b7`;
VM SHA256 starts `3d3512bd`, server SHA256 starts `67a85808`. Compiler, exporter
and wrapper remain byte-identical to the adopted tools. This is a selected
test-body engine; these results do not establish full application coverage.

Next qualify and run one new forty-command changed-source primary, retaining
ordinary native, adopted baseline, duplicate baseline, candidate session and
historical anchor arms, all original assertions, strict type/borrow rejections,
two workers and complete session CPU accounting. The first controller-qualification
admission timed out on the shared lock before any command or stage creation;
that zero-work attempt is closed and retained. No timing has been repeated.
Only a passing primary admits the full project/parser guards; current-main
integration and adoption require their own qualification.
