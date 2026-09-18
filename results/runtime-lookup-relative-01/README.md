# Direct POSIX path predicate: not adopted

The candidate replaced `PurePosixPath(name).is_absolute()` with
`name.startswith('/')` in runtime manifest validation. It preserved the other
path checks and used the already improved ancestor-walking implementation as
its baseline, commit `237510c3`.

All 22 controls and all 12 paired installed-runtime/std lookups passed. Both
modules were imported before the component clock, and every observation used
the same installation keys and physical roots. Two warmup observations were
retained separately. The fixed run completed all 27 child processes.

The performance adoption rule, recorded before execution, required negative
median paired wall and CPU differences, at least 10 of 12 faster pairs for
each metric, and negative medians in both execution-order groups. The run
failed the pair-count requirement:

| Component metric | Result |
| --- | ---: |
| Baseline median wall time | 131.755 ms |
| Candidate median wall time | 131.050 ms |
| Median paired wall difference | -3.274 ms |
| Median paired CPU difference | -3.279 ms |
| Faster pairs, wall and CPU | 8 of 12 |

All observations remain in `summary.json`, including the four slower pairs.
Both order-group medians favored the candidate, which does not override the
failed requirement. There was no retest, trimming, production adoption,
application-build claim or holdout claim. Production source and tests were
restored; experiment snapshots retain the candidate and expanded controls.

`evidence.tar.gz` retains the original plan, premeasurement README, source
freeze, source bytes, launch/supervisor records, all child receipts and raw
outputs, and the independent assessment. Its 227 logical members represent
190 physical payloads. Every member hash and the full gzip stream were checked.
Archive SHA256: `a166912e359c26ee630a099c8d76beefe4ad5484525e719305214000c54cfdbc`.
The successful execution status in the summary describes completed checks;
`component_adoption_rule_passed` is explicitly false.
