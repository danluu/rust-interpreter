# Batch required initialization in resumable Calls

Resumable E2E tool `035ef708` improves folded 10.6% and token 15.0% paired
against b2; only folded passes its original target. Exact-code samples of this
tool put 56.3% of folded and 17.4% of token thread samples in the current native
zero loop. Token also has 13.5% in native-boundary self PCs. Profiles are partial
and perturbed; these shares are neither full-run costs nor predicted savings.

Select one bounded clearing experiment before a more complex call-guard or
boundary redesign. The broader call architecture has moved formerly VM-owned
initialization into generated code. The present helper repeatedly recomputes a
range length and branches for every 16 bytes. Use a fixed 64-byte batch for
ranges statically known to contain at least 64 bytes, followed by the existing
16-byte/byte tail. Four plain pair stores clear precisely those 64 bytes; no
host memset, LLVM guest compilation, cache-line zero instruction, vector ABI
change, speculative out-of-range store or initialization elision is involved.
Smaller known ranges retain the existing helper without an extra runtime test.

The native Call already proves its complete backing and guest limits before
clearing. A callee frame's size (at least one byte) is a lower bound on the
old-live-end to new-live-end range, including alignment padding. The register
range is exactly the callee register count times 16, and remains conditional on
the existing initial-zero proof. Keep argument-copy order, all required frame
bytes, guest extents/peak, exact instruction budgets, profiling and fault order.
This changes only clearing inside the experimental resumable path. Keep the
old interpreter/tree/stub clearing as independent references.

Implement a private helper with a documented minimum-length precondition.
It uses only the existing scratch registers, bounded immediate pair offsets and
checked branch relocation. Code generation remains capacity-bounded; extra
code must not turn the original artifacts into declined-function executions.

Before measuring, execute the emitted helper on dirty storage for all offsets
modulo 64, short lengths and boundaries around 16/64/page sizes, with both
zero-length and one-past-end ranges. Verify all required bytes and untouched
prefix/suffix canaries against independent Rust slice clearing. Exercise a
conservative lower bound below the actual length. Then run the full workspace
suite in debug/release: existing recursion, descendant continuation, ABI,
capacity, working-memory, budget, warm alias-copy and TLS checks remain required.
Install an immutable tool from a committed source; rerun original-artifact
smokes to verify logical counts, correctness and code budget.

Use the original three-cycle folded/token source-edit comparison against
`b2aa6efe`, unchanged artifacts/assertions/wrong edits/limits/source restoration.
The original targets remain −10% folded/−20% token with CPU improving. Compare
candidate stages descriptively with `035ef708`; do not subtract historical runs
to claim a causal component speedup. If primary gates pass, require seven held-out
workflows (including the large projects), no unresolved >5% regression and
broader native/TLS/fre execution qualification before any retention. If they
fail, keep the failure and select from the measured remaining costs rather than
starting an open-ended sequence of batch-size or opcode tweaks.

[Folded evidence](../../../results/resumable-folded-sample-01/assessment.md) ·
[Token evidence](../../../results/resumable-token-sample-01/assessment.md) ·
[E2E evidence](../../../results/resumable-e2e-01/assessment.md)
