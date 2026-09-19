# The narrow relocation subset is too small

Five controls pass in each profile, followed by the saved actual-miss census.
The store-only, no-later-memory-read, no-live-escape subset matches154missed
Function shapes, carrying5.166ms of summed diagnostic emission across five valid
edits. The other3314previously seen changed-body misses carry203.026ms;16unchanged
bodies carry8.169ms, and1770first-worker attempts66.085ms. The narrow matches are
insufficient to justify a production relocation implementation. No runtime change
or predicted command saving follows.
[Coverage](../results/relocatable-immediate-census-02/summary.json).

Attempt01 failed at compilation because the test module was declared inside
link_tests. No test, guest or census ran. Attempt02 corrects only the declaration
and preserves the failed record. Source345a7bba completed28226/28229.

The next design to evaluate is explicit large-literal parameters: preserve common
small constants for folding, mark selected larger literals opaque in emitter facts
and derived analyses, and emit checked relocation sites when materializing their
current values. This makes the code's dependencies explicit instead of assuming
ordinary constant-folded code is independent of its literals. Native instruction
shape, current value identity, complete site accounting and all callee/scalar
inputs remain required. Execution may get slower when folds are lost, so choose
adoption only with original changed-source end-to-end benchmarks after full
correctness and fresh-emission verification. No changes to compiler ownership,
strict Rust checking or the adopted runtime.
