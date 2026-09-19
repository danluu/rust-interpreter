# Compact native switch experiment

The new candidate shortens common AArch64 switch comparisons while preserving
the complete 128-bit guest value. Its new forty-command changed-source primary
passed, but full project guards remain pending. Its session/runtime parent remains parked after the
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

The independently closed primary (`compact-native-switch-screen-token-01`,
source `c99a82ac`, closure supervisor 25706) completed all 40 commands and both
strict controls. Twelve original tests retained identical native/custom outcomes;
the wrong edit failed, final source was restored, and current custom artifacts
matched. Unreachable type/borrow errors were rejected before any session request.

| Paired edited-command metric | Candidate / adopted | A/A envelope | Ratio + envelope |
| --- | ---: | ---: | ---: |
| Wall | 0.928485 | 0.026519 | 0.955004 |
| CPU, including full server overhead | 0.914170 | 0.033507 | 0.947677 |

Both predeclared gates pass. The median candidate/native wall ratio is 1.589916
and candidate/historical-anchor ratio is 0.684761. This establishes a primary
result for the complete new composition against adopted; it does not isolate
the switch change against its separately measured parent. No runtime adoption
follows from the primary alone.

The first controller-qualification
admission timed out on the shared lock before any command or stage creation;
that zero-work attempt is closed and retained. Protocol02 then passed all16
controls and closed independently. No timing was repeated.

Next qualify the full public controller and run176-command token, folded and
pgrust histories in order, with history-off, native line-table and Cargo-check
controls added to the existing arms. Carry forward the already fixed portable
core borrow probe and JSON configuration comparison before pgrust. Private rg,
both parser guards and Nushell remain required before current-main integration.
