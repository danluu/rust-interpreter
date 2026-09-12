# Typed scalar boundary census

Both original profiles reconcile exactly against byte-identical observed artifacts. The integrated compiler remains source `5b2330c` / tool `9637b0ac`; diagnostic exporter tool `93c13c08` changes no guest bytes or VM/wrapper binaries.

| Workload | Instructions | Native Calls | Typed functions / total | Boundary rows | Analysis bounds exhausted |
| --- | ---: | ---: | ---: | ---: | ---: |
| folded-literal-trie | 4,138,403,285 | 25,913,904 | 1,045 / 1,048 | 3,335 | 0 |
| token-phrase | 13,345,235,063 | 112,236,119 | 5,375 / 5,421 | 14,852 | 0 |

The observer passed 45 exporter tests, including six new diagnostic checks; the typed profile join passed five tests. Original folded (18 bodies) and token (three bodies) assertions pass. Their artifact hashes remain `cf457940…` and `d4e13144…`. Token entropy remains in the original profile. No new guest execution occurs during profile reconciliation.

| Workload / scalar class | Argument copies | Argument bytes | Callee full loads/copy reads | Result returns | Result bytes | Callee full stores/copy writes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| folded-literal-trie / primitive | 16,349,668 | 128,265,558 | 30,196,911 | 761,474 | 789,022 | 761,474 |
| folded-literal-trie / other scalar | 4,065,855 | 32,526,840 | 2,480,543 | 82 | 1,032 | 82 |
| token-phrase / primitive | 45,997,060 | 299,261,897 | 74,440,156 | 23,208,488 | 24,193,143 | 23,250,984 |
| token-phrase / other scalar | 42,546,507 | 339,891,991 | 52,874,255 | 24,457,356 | 84,849,406 | 24,457,356 |

“Eligible” here means the bounded typed MIR/privacy/storage classification. Final bytecode promotion still requires its complete address-use and initialization proof. Other scalars use rustc’s scalar layout, separately from primitive integers/floats/bools/chars; scalar pairs and aggregates are excluded.

Entry loads and return stores within the current memory ABI would preserve the argument/result boundary copies. The next investigation is a [scalar value ABI](../../benchmarks/experiments/scalar-boundary-census/NEXT.md), starting with static admission using the existing scalar transform. This is a direction decision, not a performance claim or production change.

Unknown addresses remain explicit: token has 35.30M unknown/non-frame loads and 12.28M stores, plus 144.19M copy reads and 35.43M copy writes. These are whole-program access counts, not all boundary accesses. Indirect callee identities remain unresolved; 2.25M argument accesses are reported separately. Missing typed functions include synthetic/uncallable bodies. Spread and caller-location cases have coverage markers; no analysis exhausted its bound. Partial accesses are separately recorded and are not counted as full scalar accesses.

The first fresh export failed closed because aggregate relocation can move dedicated ABI storage. The revised observer binds by preserved argument order/width at that exact pass boundary, then checks final ABI slots and hashes each final serialized Function by numeric ID. The failed run remains [recorded](../scalar-boundary-export-smoke-01/summary.json); no guest code ran.

Full raw rows, independent unknown-address counts, all rejection groups, exact profile hashes and commands are bound by [summary](summary.json) and [terminal execution receipt](execution.json). The native boundary bytes and access counts are not latency estimates.
