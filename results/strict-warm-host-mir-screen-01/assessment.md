# Native host MIR mechanism screen

**No material improvement; keep this prototype unadopted.** The five edited complete commands have medians of 4.024730 s for baseline, 4.031534 s for candidate and 4.038854 s for the independent baseline duplicate. None of the five candidate commands reached 0.5 s. This is a mechanism screen, with no final latency qualification or holdout/generalization claim.

Median paired wall change: +0.169%; median paired CPU change: +0.102%. Maximum absolute A/A wall deviation: 5.172%; maximum absolute A/A CPU deviation: 6.695%. These descriptive deviations are not confidence intervals; a median of paired ratios can differ from a ratio of separate arm medians.

| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | B/A wall | A′/A wall | B/A CPU | A′/A CPU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1: combine-equal-and-supertype-widening-arms | 4.101143 | 3.962853 | 4.038854 | 0.966280 | 0.984812 | 0.950320 | 0.962242 |
| 2: collect-oneof-from-explicit-iterator | 3.883076 | 3.922195 | 4.083918 | 1.010074 | 1.051722 | 1.004066 | 1.059054 |
| 3: return-unrelated-widening-pair-early | 3.961683 | 4.084377 | 4.034335 | 1.030970 | 1.018338 | 1.035370 | 1.013080 |
| 4: express-subtype-test-with-is-some-and | 4.269470 | 4.246186 | 4.101528 | 0.994546 | 0.960664 | 0.969215 | 0.933050 |
| 5: make-union-pair-iterator-explicit | 4.024730 | 4.031534 | 4.023183 | 1.001691 | 0.999616 | 1.001021 | 1.008456 |

| Edit | Baseline CPU s | Candidate CPU s | Duplicate CPU s |
| --- | ---: | ---: | ---: |
| 1 | 7.056474 | 6.705910 | 6.790033 |
| 2 | 7.243228 | 7.272680 | 7.670968 |
| 3 | 6.779972 | 7.019781 | 6.868653 |
| 4 | 7.660544 | 7.424713 | 7.147667 |
| 5 | 6.905294 | 6.912344 | 6.963685 |

Complete wall time surrounds the launcher, Cargo, VM, all original selected tests and process-receipt I/O. CPU is waited-for child user plus system time; concurrent compilers can make it exceed elapsed time. Nested launcher/Cargo stages are preserved separately and are not added to complete-command wall time.

| Arm | Initial empty-target wall s | CPU s | All nine commands wall s |
| --- | ---: | ---: | ---: |
| baseline | 57.992008 | 165.859661 | 91.540102 |
| candidate | 61.141436 | 175.389195 | 94.106214 |
| duplicate | 60.330163 | 175.482051 | 92.827927 |

Each arm starts with a separate empty target/cache history. Installed-tool and standard-library setup are outside these commands. The single cold observation per arm ran in baseline/candidate/duplicate order; it does not establish a repeatable cold-build speedup or regression.

All 27 commands were validated. Each arm ran the same 14 original tests through the original source, a deliberate wrong production edit, compiled recovery, five fresh cumulative production edits and compiled final restoration. The wrong edit produced matching test failures in all arms; every other state passed all 14 tests. Executed bytecode, entry catalogs and program outputs matched across all three arms in every state. The original source was restored. All five valid edited source hashes were new within every arm’s cache history. These previously exposed Nushell edits are not fresh-project holdouts.

The candidate omits wrapper-added full MIR encoding only for unselected native host libraries in complete standard-library MIR context with an unambiguous link emission and no target or response-file arguments. Explicit user flags, selected guest export and metadata-only policy are preserved. Query-cache retention is not enabled in this screen. The installed capability and distinct exporter/wrapper hashes identify the candidate; these launcher logs contain no per-compiler host-omission counters, so no count of omitted MIR bodies is inferred from them. Cargo can replay saved compiler stderr for fresh units.

The separate [correctness qualification](../native-host-mir-build-01/assessment.md) records 91 Rust tests and four real compiler/Cargo histories. Its scope preserves ordinary native checking: metadata-only calls remain forced because otherwise uncalled constant-panic diagnostics can differ. Internal `rustc_force_inline` diagnostics in otherwise uninstantiated bodies may be forced only by legacy full MIR. This screen does not establish universal diagnostic-byte identity or justify adopting the prototype.

Baseline/duplicate tool: `923ad6d94c365365f15322ee65d32dca6ba9ccc4fd07a8147111329ea1955c86`. Candidate: `f005d3f31f03ac673208b7aac66110489d371603e4a7336de34db0da46121fab`. The VM bytes are identical. Nushell revision: `9d3157963241cf89447119d34d6e887859f5e7e8`; Cargo jobs: 4; suite workers: 2. Compiler profiles and guest flags were not reduced. The candidate was built with release debug level 1, as recorded in its frozen composition.

[summary.json](summary.json) contains all five pairs, all 27 command summaries, cold costs, source-state and artifact hashes, tool/compiler/sysroot identities and control outcomes. [evidence.json.gz](evidence.json.gz) retains exact plan, records, original summary, receipts, suites, transitions, small artifact sidecars, frozen harness/protocol/tool provenance, the original `ty.rs` with all assertions, and all nine reconstructed source states. The complete original project hash inventory and symlink identities are retained alongside the immutable Git revision; the other original Nushell files are not duplicated. All frozen inputs and retained artifact hashes were verified during initial packaging, and every archive member and deterministic gzip round trip was checked. Executable binaries, bytecode and caches remain in `.work`.

Repackage from saved source/harness snapshots after the working checkout changes, without restoring or editing that checkout:

```sh
python3 benchmarks/experiments/strict-warm-build/assess_host_screen.py \
  .work/strict-warm-host-mir-screen-01 --run-id strict-warm-host-mir-screen-01-reproduced \
  --snapshots-from results/strict-warm-host-mir-screen-01/summary.json
```
