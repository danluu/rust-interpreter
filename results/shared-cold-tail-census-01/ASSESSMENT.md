# Identical cold fault tails occupy about six percent of current code

Six independent shape, status, branch-range, resource-bound and terminal-trace
controls pass. Both saved adopted-runtime captures pass exact code/map/sample
identity checks; all 1,933/1,429 generated samples reconcile. No guest executes.

| Capture | Original bytes | Duplicate tails | Projected bytes removed |
| --- | ---: | ---: | ---: |
| Block | 11,313,812 | 15,004 | 720,192 (6.37%) |
| Exhaustive | 13,757,056 | 17,448 | 837,504 (6.09%) |

Every examined fault tail matches the source-pinned terminal shape. The model
retains a complete first tail and replaces exact later duplicates within the
same function with one branch. No assertion, budget, successor or transition
tail is shared; no generic epilogue suffix or hot check is removed. Scope spans
794/964 functions. Their sample coverage is context, not removable execution time.

Closure verifies 83 frozen inputs. This admits a bounded custom-emitter prototype
on the exact adopted Rust source fca687eb, preserving all rejected experiments
in their existing Git history. Runtime correctness and a fresh changed-source
primary are still required. Static footprint is not a measured speedup.
