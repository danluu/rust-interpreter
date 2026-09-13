# Demand-retention mechanism screen

**No material improvement; do not adopt this candidate from this screen.** The median of five edited complete commands is 4.041508 s for candidate, 4.018689 s for baseline and 3.984770 s for the independent baseline duplicate. None of the five candidate commands reached 0.5 s. This is a mechanism screen, with no final latency qualification or holdout/generalization claim.

The median paired wall change is -0.254%; median paired CPU change is +0.013%. The largest absolute A/A wall deviation is 1.780%; the largest A/A CPU deviation is 2.317%. These five comparisons and descriptive A/A deviations are not confidence intervals. A median of paired ratios differs from a ratio of separate arm medians.

| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | B/A wall | A′/A wall | B/A CPU | A′/A CPU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1: combine-equal-and-supertype-widening-arms | 4.090596 | 4.041508 | 4.056487 | 0.988000 | 0.991662 | 0.998156 | 1.023168 |
| 2: collect-oneof-from-explicit-iterator | 4.018689 | 3.990163 | 3.984770 | 0.992902 | 0.991559 | 0.994349 | 0.990486 |
| 3: return-unrelated-widening-pair-early | 3.960219 | 4.046690 | 3.976618 | 1.021835 | 1.004141 | 1.022641 | 0.997797 |
| 4: express-subtype-test-with-is-some-and | 4.066684 | 4.119639 | 4.034192 | 1.013022 | 0.992010 | 1.013095 | 0.990188 |
| 5: make-union-pair-iterator-explicit | 3.890148 | 3.880277 | 3.959386 | 0.997462 | 1.017798 | 1.000131 | 1.019633 |

| Edit | Baseline CPU s | Candidate CPU s | Duplicate CPU s |
| --- | ---: | ---: | ---: |
| 1 | 6.848584 | 6.835955 | 7.007251 |
| 2 | 7.471550 | 7.429325 | 7.400465 |
| 3 | 6.761396 | 6.914484 | 6.746503 |
| 4 | 7.140721 | 7.234232 | 7.070658 |
| 5 | 6.762911 | 6.763800 | 6.895686 |

Complete wall time surrounds the launcher, Cargo, VM, original selected tests and process-receipt I/O. CPU is waited-for child user plus system time and can exceed elapsed time because compiler processes run concurrently. Nested launcher/Cargo stages are preserved in the JSON; they are not added to complete-command time.

## Cold observations and controls

| Arm | Initial empty-target wall s | CPU s | All nine commands wall s |
| --- | ---: | ---: | ---: |
| baseline | 60.814060 | 173.573300 | 94.264848 |
| candidate | 69.871862 | 201.857217 | 102.007744 |
| duplicate | 59.491797 | 174.000462 | 91.728450 |

Each arm starts with a separate empty target/cache history; installed compiler and standard-library setup are outside these commands. The single cold command per arm was run in the planned order (baseline, candidate, duplicate). Its slower candidate observation is retained, not a repeatable cold-build regression estimate.

All 27 commands were validated. Each arm ran the original 14 tests, the deliberate wrong production edit, compiled recovery, five fresh cumulative production edits and compiled final restoration. The wrong edit produced matching guest-test failures in all arms; every other state passed all 14 tests. Bytecode and entry catalogs matched across all three arms for every state. The original source was restored. Every valid edited hash was new in each arm’s history; these exposed Nushell edits are not fresh-project holdouts.

## Retention reports and Cargo replay

| State index | Phase | Report lines | Exact earlier reports | First-seen reports | First-seen installed providers |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | cold | 712 | 0 | 712 | 36 |
| 1 | wrong-edit | 712 | 694 | 18 | 18 |
| 2 | recovery | 712 | 694 | 18 | 18 |
| 3 | edit | 712 | 694 | 18 | 18 |
| 4 | edit | 712 | 694 | 18 | 18 |
| 5 | edit | 712 | 694 | 18 | 18 |
| 6 | edit | 712 | 694 | 18 | 18 |
| 7 | edit | 712 | 694 | 18 | 18 |
| 8 | restoration | 712 | 694 | 18 | 18 |

Cargo replays stored compiler stderr for fresh units. Reports are compared by their complete JSON, including actual `process_id`, crate/test identity, incremental directories and counters. Exact records from earlier commands are excluded from newly observed counter sums. The JSON retains all first-seen process IDs, PID-reuse ambiguities, and selected-test reports. These logs lack independent compiler start-time/parentage receipts, so first-seen reports are not asserted to be an independently verified census of newly started compiler processes. Omitted promotion passes and serialized-byte counters describe mechanism activity; they do not measure time saved or establish a speedup.

## Identity and retained evidence

Baseline and duplicate tool key: `923ad6d94c365365f15322ee65d32dca6ba9ccc4fd07a8147111329ea1955c86`. Candidate key: `785432b3792154eb8df8d56fdd044fa1861b8e2652fa71414fcd9c9a9160f5ef`. VM bytes are identical; exporter and wrapper identities differ. The pinned Nushell revision is `9d3157963241cf89447119d34d6e887859f5e7e8`. Cargo jobs: 4; suite workers: 2. Compiler profile and flags were not reduced, and all required Cargo units and strict checking were retained.

[summary.json](summary.json) contains all five pairs, all 27 command summaries, cold costs, source-state hashes, artifact hashes, tool/compiler/sysroot identities and replay-aware counters. [evidence.json.gz](evidence.json.gz) preserves exact UTF-8 plan, records, original summary, receipts, suites, source transitions, small artifact sidecars, frozen harness/protocol and tool source-provenance files. Every member hash and the deterministic gzip round trip was verified. Bytecode hashes were checked against retained snapshots; caches, bytecode and executable binaries remain in `.work`.

Screen 01 failed before any workload because the inventory reader encountered a tracked directory symlink. Its [failure evidence](../strict-warm-retention-screen-01-failure/assessment.md) is preserved. Screen 02 starts fresh after that inventory fix; no timed sample was replaced.

Repackage saved evidence into a fresh result directory:

```sh
python3 benchmarks/experiments/strict-warm-build/assess_screen.py \
  .work/strict-warm-retention-screen-02 --run-id strict-warm-retention-screen-02-reproduced
```
