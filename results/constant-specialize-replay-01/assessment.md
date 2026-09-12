# Initial shared-call specialization

The prototype passes all 34 original assertions across the full saved token,
folded-trie and pgrust suites. It does not yet show enough runtime improvement
to justify the real edited-command performance screen.

| Suite | Tests | Paired median wall ratio | CPU ratio | Logical instructions, original → specialized |
| --- | ---: | ---: | ---: | ---: |
| token | 12 | 0.99310 | 0.99332 | 28,985,553,349 → 28,937,863,129 |
| folded | 18 | 0.97621 | 0.97579 | 4,139,250,391 → 4,107,786,780 |
| pgrust | 4 | 1.00315 | 1.00447 | 81,417,823 → 81,417,343 |

These are three alternating pairs per suite using the identical retained VM,
plus one entropy-recording run per suite and three untimed whole-artifact
verifications. Every artifact repeats its own instruction counts; outcomes,
test identities, per-test guest memory peaks and entropy consumption match.
The original native receipts remain the semantic reference. There are no new
Cargo builds, source edits or complete-workflow measurements in this replay.

The [offline transform](../constant-specialize-saved-01/summary.json) produces
18/9/1 shared bodies and redirects 205/74/2 static sites. Its single diagnostic
transform times are 48/16/0.5 ms, with encoded growth of 33,606/18,759/827 bytes.
The token instruction reduction is only 0.16%; the two busiest eligible callees
are absent from the clone list. The next step is to explain their declines and
correct an analysis limitation if warranted. Keep this version off main and do
not spend a full edited-workflow benchmark on it. No performance gate has been
passed or failed: the complete-workflow screen has not run.

The compiler implementation is on `experiment/constant-call-specialization-20260912`.
Build02 passed 376 workspace tests in both debug and release, with one ignored.
Build01's failed interpreter-oracle configuration remains recorded separately.
