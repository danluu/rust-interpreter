CLOSED: all five original assertions passed in ten entropy record/replay guest
commands. Baseline/candidate per-PC counts, non-timing VM counters, peak memory,
outputs and entropy agree exactly within each pair; no JIT decline occurred.
Code-map validation covered every emitted span. All changed spans are ordinary
Call transitions with the same payload and exactly48 bytes removed each; every
other operation span retains its length. Matcher qualification checked1254 full
shapes and rejected21533 single-word mutations plus shifted/truncated forms.

| Original case | Ordinary helpers replaced | Native bytes before | Native bytes after | Removed |
|---|---:|---:|---:|---:|
| ES8 exhaustive | 75 | 1207928 | 1204328 | 3600 |
| ES8 seeded | 100 | 1273704 | 1268904 | 4800 |
| Token block | 1263 | 11952720 | 11892096 | 60624 |
| Token exhaustive | 1443 | 14508196 | 14438932 | 69264 |
| Folded | 100 | 1978352 | 1973552 | 4800 |

Candidate VM f0a3abfb97fcb5f2824286f936a451de2c16e5bf66ad0e1294523293a575c345
is retained in the closed workspace snapshot. These instrumented executions prove
semantic/code-shape parity, not performance. Proceed with explicit tool composition
and the prospective changed-source ES8 screen. Scalar clearing and adopted default
remain unchanged. No passed guest needs replay for reporting.
