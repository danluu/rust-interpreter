# Additional private-array reuse has negligible scope

Do not implement this hypothetical layout change. The typed census finds only
3,116 additional bytes of possible local-extent reduction across folded's
42.5 billion recorded direct-call frame bytes, and 0.1233% for token. This is too
little scope to address the failed folded E2E gate. No production layout changed.

| Matching profile | Direct calls | Direct-call frame bytes | Hypothetical additional reduction | Share |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 25,914,348 | 42,455,137,117 | 3,116 | 0.0000073% |
| token-phrase | 110,505,461 | 33,555,764,077 | 41,382,984 | 0.1233% |

Existing scalar coloring is reconstructed exactly before proposing additional
primitive-array eligibility. Full-array assignments must overwrite every byte;
partial writes preserve incoming bytes, and ABI, address/unsupported contexts,
call destinations and entry-zero reads remain excluded. The planner retains
full-CFG liveness, dead-write interference, bounds and an independent coloring
certificate. This is a hypothetical local extent, not a final frame transform
or a prediction of CPU time saved.

The copied exporter (`71605527`) passes all 15 exporter/observer tests and uses
the exact `e89de7f8` VM binary. Fresh exports of the original folded/token batches
match the original bytecode hashes exactly; all assertions pass. Fresh profiled
executions also pass with the original options and limits. The typed weighting
tool passes three checks, validates every operation against the artifact, adds
interpreted/ordinary/native-tree counts with their separate boundaries, and
matches the VM's exact instruction total in each profile.

The observer records 1,045 folded and 5,375 token compiler instances with their
actual function IDs. All weighted direct-call frame bytes join an inventory;
there are no planner declines or unattributed direct frames. Display-name
collisions are handled by IDs. Indirect targets, entry/TLS frames and frame
alignment padding remain excluded. Guest RNG is unchanged. Counts describe
these executions; there is no new performance measurement.

Only three folded functions have a hypothetical static extent reduction.
Among executed callees, `select_root_prefilter` saves 164 bytes across 19 calls;
the frequently invoked large frames save nothing. Token's largest contribution
is `regex_automata::util::determinize::next`, 1,280 bytes across 32,278 calls.
Other layout classes dominate declared storage: 37.4 billion weighted bytes in
folded and 22.1 billion in token. Their padding/alias/lifetime constraints have
not been analyzed into a valid reuse proof; this narrow result does not rule out
all aggregate reuse.

Keep private primitive-array reuse parked alongside the earlier unused-local
and argument-only-zeroing proposals. The next selected runtime direction is
resumable native Calls with an explicit guest frame stack, so loops and cold
unsupported descendants need not exclude a whole function from native calls.
It must preserve exact VM continuations, initialization, aliases, budgets and
TLS/root completion. Existing sampled boundary/dispatcher costs motivate that
experiment; moving frame setup into native code does not remove zeroing costs.
The original `b2aa6efe` E2E gates remain unchanged.

[Counts and provenance](summary.json) ·
[Exporter qualification](../aggregate-reuse-build-01/summary.json) ·
[Original artifacts and fresh profiles](../aggregate-reuse-collection-01/summary.json) ·
[Next implementation](../../benchmarks/experiments/resumable-native-calls/PLAN.md)
