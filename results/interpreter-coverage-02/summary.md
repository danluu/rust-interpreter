# Custom interpreter: production-body edits

Strict rustc checking; selected library routines, not full applications. Cold is one build with an empty target and downloaded dependencies. Warm is one measurement for each distinct body edit. Runtime is included.

| Case | Mode | Cold build/run s | Warm build s | Warm run s | Warm total s |
|---|---|---:|---:|---:|---:|
| nushell | vm | 17.071 | 0.336 | 0.003 | 0.339 |
| pgrust-numeric | vm | 3.858 | 0.457 | 0.003 | 0.460 |

Failures: 1. Raw records: `.work/runs/interpreter-coverage-02`.
