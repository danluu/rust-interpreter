# Local-memory forwarding: complete qualification

The retained experimental custom JIT improves 25/45
real source-edit/build/test commands against the retained engine and
30/45 against native. Execution improves
29/45 pairs. The four compute workflows improve
14/20 commands and 19/20 execution stages. All 63 new artifacts exactly match their
retained counterparts, and original assertions and wrong-edit controls pass.
The production binaries are now retained as an experimental runtime improvement.

| Workflow | Faster commands vs retained | Paired command change, ms | Paired execution change, ms | Paired Cargo change, ms | Faster commands vs native |
|---|---:|---:|---:|---:|---:|
| folded-literal-trie | 3/5 | -55.547 | -126.380 | +8.603 | 0/5 |
| token-phrase | 5/5 | -279.296 | -301.287 | +0.003 | 0/5 |
| forward-anchored-tls | 3/5 | -7.131 | -13.093 | +6.788 | 5/5 |
| pgrust-sha1-inline8 | 3/5 | -30.042 | -34.386 | +1.826 | 0/5 |
| pgrust | 2/5 | +9.008 | -6.294 | +3.604 | 5/5 |
| nushell | 3/5 | -2.397 | +0.023 | -1.285 | 5/5 |
| ruff | 2/5 | +41.756 | +0.531 | +38.040 | 5/5 |
| nushell-type-relations | 2/5 | +32.729 | +0.453 | +40.824 | 5/5 |
| rg-aot | 2/5 | +0.350 | +0.168 | +0.778 | 5/5 |

Negative changes are faster. These compare five matched production edits per
workflow. Stage medians need not add to the command median. No observation is
removed or corrected for host variation, and a timing difference is not proof
of its cause. These selected library tests do not establish complete application
support or a general warm-compilation gain. Private rg-aot details stay local;
only its aggregate results appear here.

| Workflow | Cold native / retained / candidate, seconds | Edited marginal medians native / retained / candidate, seconds |
|---|---:|---:|
| folded-literal-trie | 6.904 / 7.106 / 6.968 | 2.049 / 2.791 / 2.939 |
| token-phrase | 7.886 / 11.399 / 11.462 | 1.980 / 6.820 / 6.476 |
| forward-anchored-tls | 8.012 / 5.997 / 6.053 | 1.433 / 1.115 / 1.108 |
| pgrust-sha1-inline8 | 1.364 / 0.955 / 0.836 | 0.774 / 0.885 / 0.782 |
| pgrust | 1.125 / 0.524 / 0.495 | 0.650 / 0.489 / 0.498 |
| nushell | 21.795 / 19.924 / 21.457 | 0.615 / 0.424 / 0.424 |
| ruff | 55.328 / 26.655 / 27.041 | 5.603 / 2.852 / 2.893 |
| nushell-type-relations | 74.691 / 69.133 / 70.904 | 6.345 / 4.084 / 4.016 |
| rg-aot | 3.551 / 2.794 / 2.848 | 0.537 / 0.198 / 0.192 |

Folded's paired median improves 56 ms while its marginal candidate median is 148 ms
higher. Its third and fifth commands regress 66 ms and 148 ms; its fourth execution
regresses 46 ms despite a faster command. Native remains substantially faster on
token and folded. Every other regression and cold sample remains in the tables
and individual reports.

The change forwards scalar loads and copy sources from currently available
values for exact proven local-frame ranges, initially 1/2/4/8 bytes. A bounded
16-entry table expires on register overwrite/eviction and invalidates overlaps
or unknown writes. Region boundaries reset the facts. All writes, destination
checks, final register spills, cache replacement order and instruction budgets
remain. Type and borrow checking stay with the ordinary Rust frontend.
Actual unwinding and general OS/FFI/threads remain unsupported; unavailable
operations keep explicit traps. The guest backend remains the custom
interpreter/direct AArch64 emitter.

All 183 bytecode and 11 exporter tests, 47,004 native differential commands and
245 TLS/callback checks pass. Fresh fre qualification covers 389 selected tests:
382 pass, 7 remain ignored, 382 fresh native executions pass, every fresh artifact
matches 6bf, and no JIT compilation is declined. Both measured binaries reproduce
exactly from an independent source copy and target directory.

The first build's new fault test assumed identical interpreter/JIT memory-error
messages. The retained JIT already consolidates those errors. Only the new test
comparison was corrected; budgets and other errors remain exact, and a direct
memory-state probe verifies invalid destinations receive no copy write. The
original attempt and all logs are preserved.

The completed saved-artifact screen, typed census and initial four-workflow
evidence remain in the [immutable compute-stage report](../local-memory-forwarding-compute-01/summary.md).
All 32 JIT runtime pairs improved, including added JIT generation cost. These
runtime measurements and forwarding counts do not replace the complete-command
comparisons above. Folded's full logical trace matches; token keeps its original
RNG and assertions. No deterministic seed replaces production timing runs.

Per-workflow evidence:

- [folded-literal-trie](../paired-local-memory-forwarding-folded-literal-trie-01/summary.md)
- [token-phrase](../paired-local-memory-forwarding-token-phrase-01/summary.md)
- [forward-anchored-tls](../paired-local-memory-forwarding-forward-anchored-tls-01/summary.md)
- [pgrust-sha1-inline8](../paired-local-memory-forwarding-pgrust-sha1-inline8-01/summary.md)
- [pgrust](../paired-local-memory-forwarding-corpus-pgrust-01/summary.md)
- [nushell](../paired-local-memory-forwarding-corpus-nushell-01/summary.md)
- [ruff](../paired-local-memory-forwarding-corpus-ruff-01/summary.md)
- [nushell-type-relations](../paired-local-memory-forwarding-corpus-nushell-type-relations-01/summary.md)
- [rg-aot](../paired-local-memory-forwarding-corpus-rg-aot-01/summary.md)

The retained source key is `57a54edd`; the measurements use `af9aa691`. After
qualification, one new test's comment and oracle were corrected: address 64 is
the writable frame start in that fixture, and zero-length copies accept every
address. All 183 bytecode tests pass again, and both production binaries are
byte-for-byte identical to the measured pair. No performance sample was rerun
or substituted for this test-only correction. [Exact qualification identities](qualification.json).

Retention is justified by the targeted runtime improvement, including all 32
saved-artifact JIT pairs and lower paired command medians on all four compute
workflows. The broad cohort remains mixed. The previous engine, first failed
test attempt, measured sources and complete regressions remain available. The
next diagnostic will measure remaining costs on this exact retained VM.
