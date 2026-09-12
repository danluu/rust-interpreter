# Exact test selection and native cost diagnosis

Retain `--select-test EXACT_NAME --suite-catalog CATALOG`. The catalog validates
the exact original bytecode, body identities and entry; only the in-memory
entry changes. Profiling is optional. Legacy `--profile-test` still requires
`--profile`. Missing/stale catalogs, ambiguous selectors, unknown names, entry
arguments and isolated-batch combinations fail before execution.

Source `2a39414`, tool `8a169a01`, passes 360 tests in both host profiles (one
ignored). Seven original token/folded/pgrust selections exactly match prior
instruction counts, output, memory peaks and entropy consumption using the
same recorded inputs. Tests also establish uninstrumented code dumps, unchanged
artifact bytes and preservation of selected-test failures.
[Build](../selected-native-build-01/summary.json),
[real selections](../selected-native-qualification-01/summary.json).

Three two-second sampling windows per dominant token test use fresh owned
processes, normal entropy and the original bytecode. Each code dump, live arena,
catalog selection and sample is bound to that exact process. All six executions
complete successfully. These partial, perturbed windows diagnose native paths;
their sample shares do not predict speedups or establish edited-command latency.

| Captured native category | Block boundaries | Exhaustive semantics |
| --- | ---: | ---: |
| Total thread samples | 4,611 | 4,615 |
| Generated code | 88.31% | 88.58% |
| Generated call/return entries | 26.98% | 40.56% |
| Exact clearing sequences | 7.66% | 10.47% |
| Direct register-array stores | 5.53% | 9.49% |
| Cursor remaining-budget loads/stores | 12.43% | 9.40% |
| Host heap paths | 2.30% | 6.28% |

The instruction categories overlap the broader generated entry categories;
they are not additional shares. Budget access shares do not reopen the parked
budget-register candidate: its previous complete-command screen failed.

Block boundaries concentrates in regex determinization and SipHash rounds.
Exhaustive semantics concentrates in copy preconditions, stable sorting,
vector comparison and token bounds. This explains why one generic bytecode
operation ranking is insufficient. The shared-call/DSE compiler still stays
off main after its flat/slower runtime result. Next inspect exact hot region
instructions and boundary structure for a materially different opportunity.

Evidence: [block partition](summary.json),
[block generated attribution](generated-attribution.json),
[block cursor attribution](cursor-attribution.json),
[exhaustive partition](../selected-native-exhaustive-sample-01/summary.json),
[exhaustive generated attribution](../selected-native-exhaustive-sample-01/generated-attribution.json),
[exhaustive cursor attribution](../selected-native-exhaustive-sample-01/cursor-attribution.json).
Original bytecode SHA256:
`7aee80945e3329774159cb147e58376974b5f50f6e08d68bc985c07c484ab542`.
