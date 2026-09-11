# Dense scalar frame reuse

Eight-workflow cohort complete.

The exporter colors only primitive scalar locals whose value liveness permits sharing. Arguments, results, aggregates, borrowed or projected locals, call destinations and entry-live values remain dedicated.
The pass includes every MIR successor, dead writes and simultaneous uses, preserves full frame initialization and stays within the existing analysis work bound. No inlining limits change.

The dense-set representation preserves all 1,045 captured slot maps and fallback decisions and passes nine focused tests. All eight cost pairs improve: median analysis time falls from 19.919 to 7.033 ms, with input preparation excluded equally.
The original artifact and all fourteen folded/TLS workflow artifacts exactly match the preceding allocation-heavy scalar prototype. The actual VM binary is identical to cd347.

All 143 bytecode tests, 47,004 native differential commands, compiler/launcher checks and 245 TLS checks pass.
Fresh export and execution of all 389 fre bodies preserves 381 passes, one exact prior allocation-capacity error and seven ignored tests, with 382 passing native controls.

The original folded profile has the same 26,495,637 direct calls and 4,428,759,008 logical instructions. Declared direct-callee frame volume falls from 46.219 to 42.539 GB. This excludes alignment, indirect calls and runtime TLS callbacks and is not CPU timing.
The allocation-heavy scalar execution screen improves in all six same-VM pairs (-34.580 ms paired). That screen and the analysis-cost experiment are separate from the complete production-edit measurements below.

Every workflow uses five real production edits, original unchanged assertions and a wrong edit rejected by both builds. Baseline and candidate use identical MIR settings.
Changes are medians of paired candidate-minus-parent differences; negative values are faster.

| Workflow | Native / parent / candidate medians (s) | Command change (ms) | Execution change (ms) | Wins vs parent / native |
|---|---:|---:|---:|---:|
| [folded-literal-trie](../paired-scalar-frame-dense-folded-literal-trie-01/summary.md) | 1.700 / 2.955 / 2.862 | -112.2 | -96.2 | 4/5 / 0/5 |
| [forward-anchored-tls](../paired-scalar-frame-dense-forward-anchored-tls-01/summary.md) | 1.545 / 1.265 / 1.277 | -8.6 | -1.9 | 3/5 / 5/5 |
| [pgrust](../paired-scalar-frame-dense-corpus-pgrust-01/summary.md) | 0.670 / 0.524 / 0.527 | +5.6 | -0.3 | 2/5 / 5/5 |
| [ruff](../paired-scalar-frame-dense-corpus-ruff-01/summary.md) | 5.495 / 2.785 / 2.767 | +44.7 | -0.8 | 2/5 / 5/5 |
| [nushell](../paired-scalar-frame-dense-corpus-nushell-01/summary.md) | 0.644 / 0.450 / 0.442 | -1.1 | +0.2 | 3/5 / 5/5 |
| [rg-aot](../paired-scalar-frame-dense-corpus-rg-aot-01/summary.md) | 0.558 / 0.192 / 0.196 | +3.6 | -0.0 | 2/5 / 5/5 |
| [pgrust-sha1-inline8](../paired-scalar-frame-dense-corpus-pgrust-sha1-inline8-01/summary.md) | 0.743 / 0.921 / 0.915 | -5.6 | -1.6 | 3/5 / 0/5 |
| [nushell-type-relations](../paired-scalar-frame-dense-corpus-nushell-type-relations-01/summary.md) | 11.835 / 5.771 / 5.768 | +585.1 | +0.0 | 2/5 / 5/5 |

The candidate wins 21/40 complete commands and 24/40 execution stages. It wins 30/40 against native.
Cargo variation materially affects command timings. Independent medians need not agree with medians of paired differences; all raw samples are retained.

Each workflow has only five paired production edits. Counts of wins and medians describe these samples; they do not establish statistical significance or a general speedup.

Cold successful builds use separate empty per-mode Cargo targets, with compiler tools and the standard-library MIR prepared before measurement. They are one observation per mode, reported separately from real edits.

| Workflow | Native cold (s) | Parent cold (s) | Candidate cold (s) |
|---|---:|---:|---:|
| folded-literal-trie | 7.359 | 7.483 | 7.230 |
| forward-anchored-tls | 7.358 | 5.945 | 5.799 |
| pgrust | 1.415 | 0.544 | 0.529 |
| ruff | 56.021 | 28.234 | 27.709 |
| nushell | 22.864 | 19.239 | 20.835 |
| rg-aot | 4.418 | 2.757 | 2.774 |
| pgrust-sha1-inline8 | 1.351 | 1.034 | 0.932 |
| nushell-type-relations | 70.421 | 65.902 | 63.950 |

Fresh export and execution of all 389 fre bodies yields 381 passes, one exact previous allocation-capacity error, and seven ignored tests. All 382 fresh native controls pass.
Maximum generated native code is 9,978,444 bytes; every passing guest test has zero declined functions.

All 56 artifact pairs were audited; 0 pairs are identical. Every baseline artifact exactly matches the preceding retained cd347 run.
All fourteen folded/TLS candidate artifacts also match the initial scalar prototype; their equality isolates the analysis representation change.
Native controls use standard Cargo settings; they do not establish the best available native development configuration.
These are selected library-test workflows. Whole applications, arbitrary OS/FFI calls, guest threads and native unwinding remain unsupported.
A broad warm-build improvement is not established.

Retain dense scalar-frame reuse as a targeted experimental runtime improvement. Folded trie saves a paired 112 ms per complete edited command (96 ms in execution), and TLS saves 9 ms (2 ms in execution). The full eight-workflow cohort wins 21/40 commands against cd347, 24/40 execution stages and 30/40 commands against standard native Cargo. Short workflows are effectively flat. Ruff regresses by a paired 45 ms and larger Nushell by 585 ms, mainly in Cargo; the scalar pass takes about 2 ms on larger Nushell, which does not explain its command variance. Larger Nushell cold times are 70.421/65.902/63.950 s for native/parent/candidate; this single improved cold observation does not explain the earlier cd347 cold regression. Native still wins every folded-trie/SHA-1 pair. Broad warm-build improvement and whole-application support remain unestablished. Next compare standard native Cargo, native Cargo with the same target MIR policy, and this JIT on the two compute-heavy workflows.
