# Verified operation maps

The optional diagnostic passes 436 Rust tests in each build profile, 103 Python
harness checks, seven exact real selections and three current map/profile
qualifications. All three current generated code dumps match the adopted
runtime byte for byte. Every per-PC profile, native boundary, original outcome,
memory/entropy counter, entry and assertion identity also matches.

| Current fixture | Spans | Mapped bytecode PCs | Assertion identities |
| --- | ---: | ---: | ---: |
| Token block boundaries | 492,253 | 367,117 | 2,265 |
| Token exhaustive semantics | 596,623 | 450,726 | 2,735 |
| Folded literals | 88,555 | 66,245 | 354 |

The runtime reconstructs spans after successful execution, without publishing
new code or mutating the guest. `--jit-operation-map` requires the existing
exclusive `--jit-code-dump` path and ordinary/resumable execution. The existing
map.json and code.bin stay compatible; operations.json records the finer map.
Default execution collects no spans. Capacity declines, assertions, branches,
zero-word operations, partial/invalid maps, and unsupported options are covered.

This is qualified diagnostic infrastructure, not a performance improvement.
Static byte sizes include unexecuted wrappers and tails. The next two normal-
entropy sample windows will identify which operations actually receive native
PC samples; ambiguous frames stay unassigned. Post-execution reconstruction
may appear in host samples, so the primary result is the distribution within
sampled generated code, not a claim of pure guest total-thread time.

Source 7b92125; VM83ca5b78, tool d4a6ff9a with exact adopted exporter/wrapper.
The first build's test-field compilation failure remains recorded. No runtime
speedup gate or timing campaign was repeated.

[Build](../operation-map-build-02/summary.json),
[real code and profiles](../operation-map-real-01/summary.json),
[protocol](../../benchmarks/experiments/operation-map/QUALIFICATION.md).
