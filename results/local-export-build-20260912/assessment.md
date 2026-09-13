PARK: the compiler candidate improves token build-to-ready wall by 1.985693%,
below the fixed 5% acceptance gate. All six complete histories and their controls
are valid. The compiler change remains experimental; this commit publishes
evidence only. Public confirmations were not started.

| Public workload | Edited pairs | Median wall ratio | Median CPU ratio |
| --- | ---: | ---: | ---: |
| fre token-phrase-allocation | 15 | 0.9801430665 (−1.985693%) | 0.9836448074 (−1.635519%) |
| pgrust hashfn | 15 | 1.0037879093 (+0.378791%) | 1.0045376924 (+0.453769%) |

Each ratio divides candidate by baseline for the same source state. The fixed
screen requires token wall ≤0.95, token CPU <1, pgrust aggregate wall/CPU ≤1.05,
and every history's wall/CPU median ≤1.05. Only the first requirement fails.
Every pair remains, including token history03/state2's wall ratio 1.1026411764
and CPU ratio 1.0794500097. No A/A subtraction, retiming, omitted outliers or
diagnostic samples enter these medians.

The candidate at `2c61f295d20afcbf6dd48f8840344ea9926ce83d` removes repeated
work during bytecode construction: it moves retained promotion instructions,
uses block epochs for temporary aliases, preserves instruction storage when
control flow is unchanged, reuses initialized local sizes and direct-call
classification, checks retained frame layouts without a temporary vector, and
serializes normal artifacts in one traversal. It removes repeated validation
of unchanged output while retaining the final mutation-boundary validation.
The normal serializer now grows an initially empty vector, trading its previous
size traversal for possible reallocations and copying. Individual changes were
not separately attributed in this screen.

The measured baseline is the [published owned-analysis candidate](../owned-analysis-build-20260912/assessment.md),
source commit `b0a3f17f01117fe46101513dce2f8d96f7eba8fa`, compiler key
`eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d`.
The candidate's 146 compiler inputs reproduce
`14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75`.
Both arms use the same selected VM (`03d401c1…`) and wrapper (`56fec5a3…`);
the separately retained newly linked VM (`b8dc306f…`) was not selected.
The exact source difference is retained as an unapplied evidence patch.

Correctness qualification passed 408 host tests with one ignored in each debug
and release profile, all 23,727 differential commands, and 838 supplementary
reuse/dependency/cache/audit/inlining/parity commands. A separate 90-command
late-panic qualification passed actual MIR and argument-directed bytecode
inspection in all four baseline/candidate and inline-off/on cases: a same-block
64-bit complement feeds an eight-byte store before the trap. The earlier
90-command fixture passed outcome parity but failed its intended structural
coverage because its store and panic occupied different MIR blocks. Both runs,
the failed coverage decision and the later successful inspection are retained.

The original screen controller timed out before its first admission, with no
calls or samples. The prospectively recorded recovery changed only its parent
admission wait from 300 to 3600 seconds; harness/verifier commands, namespaces,
300-second child waits, workloads and gates stayed fixed. All twelve subsequent
controller calls completed sequentially. No partial or completed history was
repeated, and the original stopped controller remains unchanged.

The [independent audit](independent-audit.md) reconstructed all 30 paired pre-VM
measurements and checked 144 primary commands, 48 independent Cargo checks and
96 physical artifact hashes. Original tests remain unchanged, wrong edits
compile then fail runtime assertions, and restored-original sources freshly
rebuild and pass after leaving the edit context. Restoration controls are
excluded from edited medians. Historical compiler inputs remain in retained
snapshots; the separate post-audit integration ledger distinguishes later root
source changes from this completed measurement.

These observations concern validated-artifact readiness before VM invocation
on the fixed public edit histories. They establish no unknown-holdout,
cold-build, full-command or runtime speedup. See [the evidence inventory](evidence.md)
for the complete retained records, lossless archives and immutable source/tool
bindings.
