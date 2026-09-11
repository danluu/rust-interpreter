# Custom interpreter: production-body edits

Strict rustc checking; selected library routines, not full applications. Cold is one build with an empty target and downloaded dependencies. Warm is one measurement for each distinct body edit. Runtime is included.

| Case | Mode | Cold build/run s | Warm build s | Warm run s | Warm total s |
|---|---|---:|---:|---:|---:|
| rg-aot | native | 3.328 | 0.316 | 0.209 | 0.549 |
| rg-aot | vm | 3.265 | 0.224 | 0.004 | 0.227 |
| pgrust-hash | native | 0.354 | 0.168 | 0.215 | 0.406 |
| pgrust-hash | vm | 0.171 | 0.161 | 0.004 | 0.165 |
| pgrust-numeric | native | 4.596 | 0.603 | 0.231 | 0.833 |
| pgrust-numeric | vm | 3.842 | 0.476 | 0.003 | 0.480 |
| fre | native | 9.549 | 1.189 | 0.262 | 1.430 |
| fre | vm | 6.482 | 0.818 | 0.003 | 0.822 |
| ruff | native | 46.394 | 2.587 | 0.250 | 2.864 |
| ruff | vm | 20.933 | 1.905 | 0.004 | 1.908 |
| nushell | native | 20.311 | 0.621 | 0.212 | 0.815 |
| nushell | vm | 15.466 | 0.341 | 0.003 | 0.344 |

Failures: 0. Raw records: `.work/runs/interpreter-edits-01`.
