# Local-memory forwarding: four completed compute workflows

The isolated custom JIT candidate improves 14 of 20 real source-edit/build/test
commands against the retained engine and five against native. Execution improves
in19/20pairs. All28 new artifacts exactly match the retained engine. Original
assertions remain, and each deliberately wrong production edit is rejected.
The retained engine is still6bf; this candidate isaf9. Full fresh fre coverage,
the remaining corpus workflows and independent reproduction are pending.

| Workflow | Faster commands vs retained | Paired command change, ms | Paired execution change, ms | Faster commands vs native |
|---|---:|---:|---:|---:|
| token-phrase | 5/5 | -279.296 | -301.287 | 0/5 |
| folded-literal-trie | 3/5 | -55.547 | -126.380 | 0/5 |
| pgrust-sha1-inline8 | 3/5 | -30.042 | -34.386 | 0/5 |
| forward-anchored-tls | 3/5 | -7.131 | -13.093 | 5/5 |

Negative changes are faster. Each row compares five matched production edits,
with complete cold commands and wrong-edit controls retained separately. Cargo,
export and execution costs remain inside each command. No observation is removed
or corrected for host variation. These are selected library-test workflows;
they do not establish whole-application support or a general warm-build gain.

| Workflow | Cold native / retained / candidate, seconds | Edited marginal medians native / retained / candidate, seconds |
|---|---:|---:|
| token-phrase | 7.886 / 11.399 / 11.462 | 1.980 / 6.820 / 6.476 |
| folded-literal-trie | 6.904 / 7.106 / 6.968 | 2.049 / 2.791 / 2.939 |
| pgrust-sha1-inline8 | 1.364 / 0.955 / 0.836 | 0.774 / 0.885 / 0.782 |
| forward-anchored-tls | 8.012 / 5.997 / 6.053 | 1.433 / 1.115 / 1.108 |

Folded's paired median improves56ms, but its candidate marginal median is148ms
higher. Its third and fifth commands regress66ms and148ms; its fourth execution
regresses46ms despite a faster full command. Token's cold command regresses63ms,
and TLS's56ms. Keep these disagreements and regressions in the assessment.

The implementation forwards scalar loads and copy sources only from values
still available for the exact proven local-frame range, initially1/2/4/8bytes.
A bounded16-entry table expires on register overwrite or cache eviction and
invalidates overlaps or unknown writes. Region boundaries start with no facts.
All stores, destination checks, final register spills, instruction accounting,
cache replacement order and ABI behavior remain. The Rust frontend keeps its
ordinary type and borrow checking. Actual unwinding and general OS/FFI/threads
remain unsupported; unavailable operations keep explicit traps.

All183bytecode tests,11unchanged exporter tests,47,004native differential
commands and245TLS/callback checks pass. The first attempt exposed a mistake in
the new test's expected error text: retained JIT memory faults use a consolidated
message. Only that new test comparison was corrected; instruction-budget and
other errors remain exact, and a direct memory-state probe verifies that an
invalid copy destination receives no write. The failed attempt is preserved.

The original-artifact runtime screen uses eight alternating pairs per workload.
All32JIT pairs improve: paired elapsed savings are275mstoken,128msfolded,
35msSHA-1 and10msTLS. The interpreter control wins4/8 with a2ms paired saving.
JIT generation takes an additional7.2ms,3.1ms,0.23ms and1.53ms respectively;
those costs are already included in the runtime totals. This screen alone is
not an end-to-end result.

The typed census reaches246million forwarded accesses in the saved folded
profile and659million in token; the same called function IDs emit190,020 and
375,104fewer native bytes. These counts are not latency or speedup estimates.
Folded's complete logical profile matches the retained engine. Token preserves
its real RNG and original assertions;17functions differ in the two observed
profiles. No deterministic seed replaces the production timing runs.

The exporter binary differs despite unchanged production MIR-lowering source.
Both exact binary hashes, source hashes, original assertions and fresh artifact
identity checks are recorded. Independent reproduction is still pending.

Per-workflow reports:

- [token-phrase](../paired-local-memory-forwarding-token-phrase-01/summary.md)
- [folded-literal-trie](../paired-local-memory-forwarding-folded-literal-trie-01/summary.md)
- [pgrust-sha1-inline8](../paired-local-memory-forwarding-pgrust-sha1-inline8-01/summary.md)
- [forward-anchored-tls](../paired-local-memory-forwarding-forward-anchored-tls-01/summary.md)
