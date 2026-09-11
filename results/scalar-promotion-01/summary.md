# Scalar promotion: full original benchmark set

The candidate improves the runtime-heavy fre workflows and SHA-1, but remains isolated because the larger Nushell workflow regressed. Across nine workflows, it wins 27/45 real edited commands against the retained engine and 31/45 against native compilation. These counts describe these samples; they do not establish a general warm-build improvement. Root88c01c remains retained; candidate81e014 is not integrated.

Each workflow contains five real production edits, the original tests, independent compiler caches, a fresh native control, and a deliberately incorrect edit that must fail. Unchanged commands serve as setup or correctness controls. Paired changes below are candidate minus retained; negative is faster.

| Workload | Wins vs retained | Paired command change | Execution change | Wins vs native |
| --- | ---: | ---: | ---: | ---: |
| [Folded search](../paired-scalar-promotion-moves-folded-literal-trie-01/summary.md) | 4/5 | -121.9 ms | -63.1 ms | 0/5 |
| [Token phrases](../paired-scalar-promotion-moves-token-phrase-01/summary.md) | 5/5 | -218.3 ms | -189.1 ms | 0/5 |
| [TLS search](../paired-scalar-promotion-moves-forward-anchored-tls-01/summary.md) | 3/5 | -33.5 ms | -17.9 ms | 5/5 |
| [SHA-1](../paired-scalar-promotion-moves-pgrust-sha1-inline8-01/summary.md) | 5/5 | -18.5 ms | -22.6 ms | 1/5 |
| [pgrust](../paired-scalar-promotion-moves-corpus-pgrust-01/summary.md) | 2/5 | +3.3 ms | -1.2 ms | 5/5 |
| [Nushell](../paired-scalar-promotion-moves-corpus-nushell-01/summary.md) | 3/5 | -0.2 ms | -0.0 ms | 5/5 |
| [Ruff](../paired-scalar-promotion-moves-corpus-ruff-01/summary.md) | 2/5 | +30.1 ms | -1.8 ms | 5/5 |
| [Nushell type relations](../paired-scalar-promotion-moves-corpus-nushell-type-relations-01/summary.md) | 1/5 | +378.2 ms | +0.0 ms | 5/5 |
| [Private rg-aot](../paired-scalar-promotion-moves-corpus-rg-aot-01/summary.md) | 2/5 | +4.4 ms | -0.1 ms | 5/5 |

The larger Nushell case regresses by 378.2 ms, including a 360.8 ms paired increase in Cargo. The scalar pass itself takes a median 1.977 ms in those edited builds. The cause of the larger difference is not established. Two independent repetitions and a separate instrumented diagnostic are now complete; their results are described below. All original samples, including the token workflow’s 8.824-second retained sample, remain in the evidence.

Cold build-and-test commands are recorded separately:

| Workload | Native | Retained | Candidate |
| --- | ---: | ---: | ---: |
| Folded search | 7.754 s | 7.881 s | 8.215 s |
| Token phrases | 8.323 s | 12.685 s | 11.868 s |
| TLS search | 7.211 s | 6.011 s | 5.780 s |
| SHA-1 | 0.917 s | 0.841 s | 0.834 s |
| pgrust | 0.863 s | 0.523 s | 0.501 s |
| Nushell | 24.147 s | 23.525 s | 22.133 s |
| Ruff | 67.062 s | 36.358 s | 34.369 s |
| Nushell type relations | 75.391 s | 64.046 s | 68.125 s |
| Private rg-aot | 3.785 s | 2.936 s | 2.954 s |

The folded candidate’s cold command regresses by 334 ms. The larger Nushell cold command regresses by 4.079 s. Stage medians are calculated separately and do not sum to command medians. No samples or startup costs were discarded.

The implementation promotes eligible private primitive MIR slots to VM registers, preserves entry initialization and the memory ABI, and forwards scalar captures only while their source value remains unchanged within a block. It retains captures needed after overwrites or across block boundaries. The measured folded export promotes 1,182 slots, removes 7,143 address operations and 3,405 redundant moves, and spends 11.624 ms in the new pass. Guest execution still uses the custom interpreter/direct AArch64 emitter with strict rustc checking.

Validation passes 168 bytecode tests, 11 exporter tests, 47,004 native differential checks, and 245 TLS/callback checks. Fresh exports of the complete fre cohort pass all 382 active tests against 382 fresh native executions; seven tests remain ignored. All 382 body hashes change, and every passing JIT case reports zero declined functions. Maximum emitted native code in that cohort is 9,381,404 bytes.

All 63 freshly produced baseline workflow artifacts match their historical inputs. The 63 candidate workflow artifacts are retained and hash-verified. Every workflow restores its source pin, preserves original assertions, and rejects its wrong edit. Private results are reported as aggregates. This validates selected existing library tests in large repositories; whole applications, general native unwinding, arbitrary FFI and guest threads remain outside the demonstrated coverage.

The earlier experiments remain part of the evidence. Scalar promotion alone reduced executed bytecode from 4.429B to 4.251B but lost all six runtime pairs, with a 459 ms paired regression. A diagnostic attributed a major new cost to 34.581 GB of logical register clearing across 4.202M calls. An entry-aware proof removes that clearing, but the combined intermediate candidate wins only 3/8 against the retained engine. The final move-forwarding version reduces executed bytecode to 4.138B and wins 6/6 runtime pairs, saving 48.4 ms against retained. These runtime filters do not replace the edited-command measurements above.

The initialization proof has an independent 38,416-shape control-flow oracle and tests for poisoned reused registers. Two early inlining-heuristic assertion failures, the initial preparation-only copy error, the corpus harness’s incorrect exporter-binary identity assumption, and the fre disk preflight refusal are preserved. The exporter keeps the earlier inlining proof separate from the runtime proof. The corrected corpus harness verifies actual newly exported baseline artifact equality.

Raw reports, profiles, hashes, source versions and failure records are indexed in [summary.json](summary.json). The next action is to investigate the larger Nushell regression before any integration.

The independent same-order Nushell repetition passes with all seven candidate
artifact hashes identical to the first run. It wins 3/5 and has a paired
−136.1 ms command change (Cargo −144.1 ms). A third run reverses each positive
edit's mode order and gives 2/5 wins, +101.8 ms command and +90.1 ms Cargo.
All seven baseline and candidate artifact pairs match across the three runs.
These runs total 6/15 wins and preserve the original regression. The ordering
association does not establish a causal explanation. Repetition cold commands
are 76.820/66.670/64.646 s and 75.083/69.139/66.140 s for native/retained/candidate.

A fourth run adds Cargo unit timing and child CPU counters and is excluded from
performance qualification. It verifies the same artifacts and all original
assertions, and records 19 rebuilt units per edited command. The selected test
target starts after several seconds of native host compilation and dependency
checking. In its largest regression, 1.04 s of the 1.30 s command difference is
before that target starts; the target duration adds 0.25 s. Child user/system CPU
rises by 0.23 s, and the reported major-fault counter rises by 51,786. These
measurements locate the variation but do not identify its system-level cause.
The paired lowering increase is 4.2 ms; guest execution changes by −0.2 ms.
[Instrumented diagnostic](../scalar-promotion-cargo-diagnostic-04/summary.md).

Keep scalar promotion isolated. The next bounded experiment starts from retained88
and changes only forced MIR retention for native host libraries when Cargo has
explicitly separated host and guest targets. It preserves ordinary checking,
native build scripts/macros, and guest MIR retention. The native host nu-protocol
unit takes a median 1.90 s in the diagnostic baseline, overlapping other work;
that is an opportunity to test, not a predicted saving. Real edited commands
and unchanged guest artifact hashes must decide whether the policy helps.

The subsequent [identical-tool control](../identical-tool-control-01/summary.md) reproduces large warm-command swings with no implementation difference: +181 ms median slot difference and up to 1.68 s per edit. This limits attribution of the earlier Nushell timing differences. It is not valid to subtract the separate control as a correction or to conclude that either candidate has zero effect. Both remain isolated while a consecutive-edit protocol is evaluated.
