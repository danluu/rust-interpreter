# Persistent-register folded-trie profile

Three fresh executions of source `d664bce` / tool `e89de7f8` pass the original
artifact's assertions with native calls, call stubs and persistent registers.
All processes are task-owned; no unrelated work was controlled. Same-process
published code bytes/ranges, PID, artifact hash and runtime options are verified.
All generated PCs resolve: 1,074 generated samples
among 2,557 captured thread samples.

| Observed category | Share of thread samples |
| --- | ---: |
| VM frame reservation | 24.9% |
| Native boundary | 11.6% |
| VM dispatcher self | 11.9% |
| Generated zeroing | 9.0% |
| Direct register-array stores | 3.6% |
| Direct register-array loads | 0.5% |
| Cursor loads/stores | 2.4% |
| Generated ABI byte-copy loops | 0.0% |

These are partial perturbed windows, with the original guest RNG. The listed
rows are a selected subset of the disjoint classification; omitted generated
and host instructions remain in the JSON report. Entry kinds include wrappers
and failure tails. These shares are neither opcode costs nor predicted savings;
changes from a separate capture do not establish a causal speedup.

The end-to-end candidate passes the token gate but misses folded. Frame
reservation/initialization remains material, especially for folded; the next
scope diagnostic will examine fully initialized private ranges with disjoint
lifetimes. It must preserve padding, aliases and the existing byte contract.
Existing unused-local and argument-only zeroing work stays parked.

[Disjoint samples](summary.json) · [Exact-code attribution](generated-attribution.json) ·
[Real edit result](../persistent-e2e-01/assessment.md) ·
[Frame-reuse constraints](../../benchmarks/experiments/bounded-native-calls/FRAME-REUSE-REVIEW.md)
