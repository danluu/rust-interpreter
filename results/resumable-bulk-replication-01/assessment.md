# Fixed-tool replication

Both original runs remain in the record. Each gate uses its own fifteen
edited pairs; no pooled retention criterion or repeated attempt is used.

| Workload | Run | Paired wall change | Paired CPU change | Original gate |
| --- | --- | ---: | ---: | --- |
| folded-literal-trie | resumable-bulk-e2e-01 | -19.51% | -20.60% | pass |
| folded-literal-trie | resumable-bulk-e2e-02 | -19.15% | -19.48% | pass |
| token-phrase | resumable-bulk-e2e-01 | -19.95% | -20.54% | fail |
| token-phrase | resumable-bulk-e2e-02 | -19.97% | -20.07% | fail |

All 336 commands, including 84 independent Cargo checks, are preserved.
There are 60 edited pairs across both workloads and 168 verified artifacts.
Corresponding engines receive identical bytecode. Cross-cycle bytecode
layout differences remain unresolved; matching corresponding histories
across these two runs would not prove general determinism.

Per-edit wall/CPU variation is descriptive. These six samples per edit
share cache-history and host conditions; no independent-sample confidence
interval, unique-case count or significance claim is inferred.

## folded-literal-trie

The original gate classification agrees between runs.

| Edit | Run | Wall ratio median [min, max] | CPU ratio median [min, max] |
| --- | --- | ---: | ---: |
| test-ascii-leading-bit | 01 | 0.8031 [0.7893, 0.8265] | 0.8007 [0.7824, 0.8018] |
| test-ascii-leading-bit | 02 | 0.7889 [0.7887, 0.8073] | 0.7854 [0.7719, 0.7882] |
| express-continuation-prefix-as-shift | 01 | 0.8151 [0.7660, 0.8279] | 0.7798 [0.7654, 0.7901] |
| express-continuation-prefix-as-shift | 02 | 0.7752 [0.7514, 0.8849] | 0.8016 [0.7863, 0.8408] |
| name-root-membership-mask | 01 | 0.8650 [0.7388, 0.8787] | 0.7962 [0.7790, 0.8120] |
| name-root-membership-mask | 02 | 0.8474 [0.8085, 0.8530] | 0.8156 [0.8107, 0.8442] |
| name-two-byte-scalar-fields | 01 | 0.8049 [0.7059, 0.8426] | 0.7940 [0.7713, 0.7975] |
| name-two-byte-scalar-fields | 02 | 0.8007 [0.7326, 0.8375] | 0.7927 [0.7543, 0.8232] |
| match-first-byte-explicitly | 01 | 0.8004 [0.7535, 0.8064] | 0.7949 [0.7852, 0.8044] |
| match-first-byte-explicitly | 02 | 0.8243 [0.8170, 0.8608] | 0.8068 [0.8052, 0.8137] |

## token-phrase

The original gate classification agrees between runs.

| Edit | Run | Wall ratio median [min, max] | CPU ratio median [min, max] |
| --- | --- | ---: | ---: |
| name-literal-finder-result | 01 | 0.7909 [0.7735, 0.8240] | 0.7930 [0.7904, 0.7946] |
| name-literal-finder-result | 02 | 0.8005 [0.7891, 0.8271] | 0.7993 [0.7807, 0.8000] |
| reuse-short-count-input-length | 01 | 0.7934 [0.7806, 0.8315] | 0.7983 [0.7836, 0.8029] |
| reuse-short-count-input-length | 02 | 0.7976 [0.7625, 0.8052] | 0.8003 [0.7618, 0.8021] |
| reuse-short-span-input-length | 01 | 0.8005 [0.7888, 0.8608] | 0.8016 [0.7906, 0.8031] |
| reuse-short-span-input-length | 02 | 0.8071 [0.8031, 0.8224] | 0.8023 [0.7895, 0.8076] |
| orient-short-route-width-comparison | 01 | 0.8039 [0.7715, 0.8219] | 0.7921 [0.7917, 0.8052] |
| orient-short-route-width-comparison | 02 | 0.7736 [0.7594, 0.7951] | 0.7807 [0.7753, 0.7949] |
| match-short-route-event-bound | 01 | 0.8091 [0.7618, 0.8454] | 0.7993 [0.7893, 0.8089] |
| match-short-route-event-bound | 02 | 0.8003 [0.7924, 0.8260] | 0.8000 [0.7961, 0.8002] |

The measured mode remains experimental. Broader execution qualification and
seven held-out workflows are still required before retention. Native
profile/jobs, setup exclusions and whole-application limitations remain
those of the original protocol. No unrelated workload was controlled.

[All pairs and evidence hashes](summary.json) ·
[Protocol](../../benchmarks/experiments/resumable-native-calls/REPLICATION.md)
