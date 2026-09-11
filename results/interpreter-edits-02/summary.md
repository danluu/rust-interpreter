# Custom interpreter: production-body edits

Strict rustc checking; selected library routines, not full applications. Cold is one build with an empty target and downloaded dependencies. Warm is one measurement for each distinct body edit. Runtime is included.

| Case | Mode | Cold build/run s | Warm build s | Warm run s | Warm total s |
|---|---|---:|---:|---:|---:|
| rg-aot | native | 3.450 | 0.308 | 0.208 | 0.503 |
| rg-aot | vm | 3.015 | 0.199 | 0.003 | 0.203 |
| pgrust-hash | native | 0.385 | 0.170 | 0.212 | 0.382 |
| pgrust-hash | vm | 0.193 | 0.167 | 0.004 | 0.170 |
| pgrust-numeric | native | 4.605 | 0.589 | 0.228 | 0.821 |
| pgrust-numeric | vm | 3.807 | 0.446 | 0.003 | 0.450 |
| fre | native | 8.967 | 1.167 | 0.199 | 1.364 |
| fre | vm | 5.625 | 0.818 | 0.004 | 0.824 |
| ruff | native | 50.852 | 2.877 | 0.262 | 3.122 |
| ruff | vm | 22.412 | 1.986 | 0.003 | 1.989 |
| nushell | native | 21.129 | 0.586 | 0.211 | 0.782 |
| nushell | vm | 15.382 | 0.345 | 0.003 | 0.348 |

Failures: 0. Raw records: `.work/runs/interpreter-edits-02`.
