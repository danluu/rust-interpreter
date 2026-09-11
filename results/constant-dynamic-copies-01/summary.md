# Guarded constant-sized dynamic copies

A separate diagnostic of the original exhaustive token-phrase test observes 11,913,117 dynamic copies: 95.1% are 24 bytes and 99.8% are at most 128 bytes. A typed static proof identifies 11,189,104 executed copies whose small size follows immediately from an integer literal or two literals, unsigned 64-bit multiplication and its overflow assertion. No branch may enter inside the defining sequence. Eligibility does not use function names, observed sizes or inputs. Diagnostic timings are excluded from performance evidence.

The candidate keeps the original bytecode and overflow assertion, and reuses the existing native Copy emitter for those proven counts. Other dynamic copies stay in the interpreter. Full range validation, readonly storage, overlap, cache eviction, original logical instruction counts and code-size limits remain active. All 169 bytecode tests pass, including region splits and partial-budget tails. Two controlled RNG-input pairs preserve original assertion outcomes and full logical per-PC traces.

The six-pair same-artifact screen removes about 11.1 million VM-to-native entries on token-phrase but saves only a paired 32.6 ms, with large variation and 4/6 wins. SHA-1 saves 9.8 ms in all six pairs; TLS saves 1.9 ms in all six. Folded is effectively flat, and the interpreter control changes by −1.6 ms. Counts alone do not establish an execution-time gain. All samples, including regressions, are retained.

| Production-edit workflow | Native / parent / candidate median | Paired command change | Execution change | Parent / native wins |
|---|---:|---:|---:|---:|
| [token-phrase](../paired-constant-dynamic-copy-token-phrase-01/summary.md) | 2.476 / 7.121 / 7.201 s | -31.4 ms | -76.3 ms | 3/5 / 0/5 |
| [pgrust-sha1-inline8](../paired-constant-dynamic-copy-pgrust-sha1-inline8-01/summary.md) | 0.791 / 0.805 / 0.803 s | -6.2 ms | -11.2 ms | 3/5 / 3/5 |

Each completed workflow recompiles five actual cumulative production edits, preserves the original tests, rejects a wrong production edit, and verifies all seven exported source states against the retained bytecode. The exporter binary differs despite unchanged lowering source, so exact artifact checks are required. Both custom engines use the same options, including explicit150k allocations for token-phrase. Native Cargo remains a separate control. Cold timings and complete samples are in the linked reports.

The candidate is parked without integration. It wins 6/10 complete commands against the parent and 3/10 against native. The execution-stage savings are real in this cohort, but the small and mixed end-to-end benefit does not justify prioritizing broader qualification over the next hypothesis. The 169 tests and focused traces passed; this is not a correctness rejection. The broader native/TLS/fre gates were prepared but not run for this candidate. Source, binaries, raw samples and diagnostics remain archived. Root stays88c01c. No broad warm-build improvement is established.
