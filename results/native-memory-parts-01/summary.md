# Redundant native memory instructions

An isolated AArch64 emitter removes overwritten load-result clears and high-half reads that narrow stores never consume. Loads up to eight bytes still publish a zero high half; odd widths retain the required byte-assembly initialization, and zero-byte loads still yield zero. Copies preserve complete-range checks, overlap behavior and register-cache eviction. Bytecode, native-region boundaries, logical instruction budgets, the exporter binary, strict type checking and borrow checking are unchanged.

A typed compile-only observer labels the proposed removals without changing any emitted machine-code byte. Weighting those labels by existing successful block hits finds 7,587,162,459 redundant instruction executions in token-phrase and 2,131,543,736 in folded-trie. These are not CPU-time or memory-traffic measurements. Actual generated code shrinks by exactly the predicted 929,244 and 381,328 bytes.

All 169 bytecode tests pass, including new checks for widths 0–16, zero extension, stale high halves, incoming/cached/constant/local values, distant registers, aliases, readonly and heap boundaries, overlapping copies through width128, exact instruction budgets, native-region splits and code-cap fallback. The complete folded logical trace matches. Production RNG makes the exhaustive token-phrase trace vary slightly between processes; no controlled RNG-input trace comparison was run for this candidate.

| Same-artifact execution | Candidate wins | Paired change | Parent / candidate median |
|---|---:|---:|---:|
| token-phrase | 4/6 | -26.85 ms | 5.431726 / 5.457913 s |
| folded | 3/6 | -17.42 ms | 1.834902 / 1.833272 s |
| sha1 | 5/6 | -1.77 ms | 0.272065 / 0.269915 s |
| tls | 6/6 | -3.82 ms | 0.217835 / 0.213849 s |
| pgrust-interpreter | 2/6 | +0.93 ms | 0.368277 / 0.365692 s |

All samples are retained, including token-phrase pairs of −756 and −489 ms and a folded pair of −239 ms. Smaller paired medians and substantial variation do not support a large speedup claim. The unchanged interpreter path serves as a control.

| Production-edit workflow | Native / parent / candidate median | Paired command change | Execution change | Parent / native wins |
|---|---:|---:|---:|---:|
| [token-phrase](../paired-native-memory-parts-token-phrase-01/summary.md) | 2.428 / 7.118 / 7.194 s | +170.3 ms | -10.6 ms | 2/5 / 0/5 |
| [folded-literal-trie](../paired-native-memory-parts-folded-literal-trie-01/summary.md) | 1.751 / 2.804 / 2.745 s | -16.5 ms | -6.3 ms | 3/5 / 0/5 |

Each workflow recompiles five cumulative production edits and preserves the original tests. A deliberately wrong edit must fail in native, parent and candidate engines. All seven exported states are identical to the retained engine. Cold commands, Cargo/execution stages and complete samples are in the linked reports. These are selected library-test workflows, not whole applications.

Parked without integration: only five of ten complete edit commands improve, with no native wins. Token-phrase regresses by a paired170ms per command while execution saves11ms; folded-trie saves16ms per command and6ms in execution. The observed removal of billions of generated instructions produces little end-to-end benefit in this cohort. This is a performance-priority decision, not a correctness rejection. Retain the source and complete measurements; use a fresh CPU sample to choose the next change. Root remains88c01c.

The broader native differential, TLS and complete fre replay gates were prepared but have not run for this candidate. No broad warm-build improvement is established.
