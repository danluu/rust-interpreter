# Compact native switch experiment

The new candidate shortens common AArch64 switch comparisons while preserving
the complete 128-bit guest value. Its new forty-command changed-source primary
passed, but the full private wall regression gate failed. No runtime adoption follows. Its session/runtime parent remains parked after the
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

The full public controller now passes27 controls and is independently closed
(`compact-native-switch-guard-protocol-02`, source`59c151db`, closure78117).
These cover12 accounting,6 command,5 controller/admission tests and4 actual
pinned-rustc type/borrow rejections across std and no_std. The prior26-control
qualification is also retained: a review before timing found that the benchmark
still expected22 controls. Protocol02 corrects admission, adds its regression
control, and validates the actual produced summary through the benchmark
admission function. Neither qualification executes a project guest or times an
edited command.

The full token history (`compact-native-switch-edit-token-01`, source`4abcd34d`,
independent closure97579) also passes. All176 commands and both strict controls
preserve the12 original test outcomes, expected wrong-source failures, final
restoration and current custom artifact identity. The closure verifies2,065
frozen inputs and654 retained evidence files.

| Full token metric | Candidate / adopted | A/A envelope | Ratio + envelope |
| --- | ---: | ---: | ---: |
| Wall | 0.956804 | 0.026161 | 0.982965 |
| CPU, including full server overhead | 0.945226 | 0.021166 | 0.966392 |

The complete composition reduces median paired edited-command wall time4.3%
and CPU5.5% against adopted. It still takes1.643992 times native wall time.
The history-enabled/history-off wall ratio is1.003058 and CPU ratio0.992346;
these close values do not establish a separate history-cache latency benefit.
The primary and full-history results remain distinct measurements, with no
isolated switch-versus-parent claim.

The full folded-literal guard (`compact-native-switch-edit-folded-01`,
source`242ad5d3`, independent closure41841) passes176 commands and both strict
controls, with all18 original tests preserved. The closure checks2,068 inputs
and642 evidence files. Wall/adopted is0.983587 with A/A0.043175, giving margin
1.026762 under the1.05 regression bound. CPU/adopted is0.972522 with A/A0.016140,
margin0.988662. Native wall ratio is0.973575. This passes the regression guard;
the wall difference is inside its measured variation and is not a clear gain.

The full pgrust hash-function guard (`compact-native-switch-edit-pgrust-01`,
source`9874477b`, independent closure74098) passes176 commands and both strict
controls, retaining all4 original tests. Its closure checks5,357 inputs and588
evidence files. Wall/adopted is1.001753 with the predeclared per-edit median A/A
envelope0.016019, margin1.017771; CPU/adopted is0.995725 with A/A0.021030,
margin1.016754. Native wall ratio is1.120580. This is a neutral regression pass.
The worst individual A/A deviations are36.29% wall and33.32% CPU; all pairs
remain recorded, and the original median-based gate is unchanged.

The private rg-aot history (`compact-native-switch-edit-rg-aot-01`,
source`43aa2344`, independent closure35058) completes176 commands and both strict
controls with its original test, exact outcomes/artifacts and source restoration.
Its closure verifies678 inputs and794 local evidence files. Private names,
source and artifacts remain in the owned local evidence.

| Private regression metric | Candidate / adopted | A/A envelope | Ratio + envelope |
| --- | ---: | ---: | ---: |
| Wall | 1.010025 | 0.044826 | 1.054851 |
| CPU, including both session slots | 1.007557 | 0.017173 | 1.024730 |

The wall margin exceeds the predeclared1.05 bound, so the campaign is PARKED.
The observed1.0% wall difference is smaller than A/A variation; the failed
engineering gate does not establish a separate runtime regression or its cause.
Native wall ratio remains0.574904. No pair is discarded, no gate is relaxed,
and no unchanged timing is repeated. Both parser profiles and Nushell are
cancelled without starting; their prepared controllers are retained.

Next isolate the compact switch emitter on the adopted scratch/scalar runtime.
The current tests establish switch semantics, while this campaign measures the
complete session/indirect/readonly/successor composition. A fresh candidate with
only the emitter change will directly test that mechanism against adopted, with
fresh correctness qualification and unchanged end-to-end gates. First recover
build headroom through exact, closed, owned compiler-cache retirement.

The large/private adapter binds the actual27-control portable proof02 in code;
its frozen planning note still names the earlier proof01. That stale prose does
not select the proof or change the actual source/diagnostic checks.
