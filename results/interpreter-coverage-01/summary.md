# Custom interpreter: production-body edits

Strict rustc checking; selected library routines, not full applications. Cold is one build with an empty target and downloaded dependencies. Warm is one measurement for each distinct body edit. Runtime is included.

| Case | Mode | Cold build/run s | Warm build s | Warm run s | Warm total s |
|---|---|---:|---:|---:|---:|
| pgrust-hash | vm | 0.169 | 0.157 | 0.004 | 0.161 |
| fre | vm | 6.018 | 0.791 | 0.003 | 0.795 |

Failures: 1. Raw records: `.work/runs/interpreter-coverage-01`.
