All five declared gates pass across 726 changed-source build/test commands. The continuation retained 594 completed commands and ran only the original 132-command Nushell case; no command was repeated. All 9,005 frozen inputs, source pins/restoration and retained artifact hashes pass the final audit. The separately qualified original pgrust parser still passes all 114 tests.

| Selection | Candidate / prior custom wall | CPU | Candidate / ordinary native wall | Decision |
| --- | ---: | ---: | ---: | --- |
| token phrase | 0.9527 | 0.9617 | 1.6410 | primary passes |
| folded matching | 0.9861 | 0.9907 | 0.9270 | guard passes |
| pgrust hashfn | 0.9984 | 0.9983 | 0.8719 | guard passes |
| private rg-aot | 1.0045 | 1.0019 | 0.4077 | guard passes |
| Nushell type relations | 1.0011 | 0.9971 | 0.6119 | guard passes |

Ratios are medians of within-state pairs, not ratios of independent stage medians. Token improves 4.73% wall and 3.83% CPU against the prior custom runtime, beyond its 1.714%/1.583% A/A envelopes. The other rows establish the declared regression guards; their changes do not establish incremental runtime gains. The pgrust performance guard selects four hashfn tests and Nushell selects 14 type-relation tests. These are not whole-project performance claims.

Nushell wall/CPU A/A envelopes are 4.0450%/0.8368%; the corresponding ratio-plus-envelope margins are 1.041596/1.005474, each within the frozen 1.05 guard. The earlier original disk refusal and the continuation lock timeout remain recorded. Verified compiler-cache retirement restored admission headroom without deleting protected evidence or controlling another workload.

The measured tool is317a0bf16da0f15f562ab457408ab321b12f25211f8169ec8bcd8205a3cb7dfb, with VMf0e5f2ea9bbe411c7309ae7283f8040b0549759344c5f81798c1e2eae9e99d9b and the unchanged b08f39e2 exporter/wrapper. Qualification includes504 workspace tests per profile,119 strict/cache/Cargo controls, three exact profiles and13 original execution controls. Keep the16 MiB code default. The large parser-function decline is still present; this result does not solve it.

Proceed with the conditional main integration and qualify its newer compiler components. Do not repeat the timing campaign or attribute these complete-command ratios automatically to newer optional compiler routes. Private command and source details remain local.
