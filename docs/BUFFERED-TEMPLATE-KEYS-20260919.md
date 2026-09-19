# Buffered template keys: qualified, parked after diagnostics

The fixed 4 KiB buffer preserves the exact serialized v3 key and complete-write
size limit. It passes 658 Rust tests in each profile (16 ignored), 33 diagnostic
integrations, 10 unbuffered session controls, 24 unbuffered model controls and the
default VM build. The unchanged Python record binds 442 passed and 22 skipped.
[Qualification](../results/buffered-template-keys-qualification-01/summary.json).

The actual saved parser history passes all 16 suites and 1,824 test invocations,
including the original wrong-edit failure text. Independent fresh emission verifies
all 16,155 cache hits. [Verification](../results/buffered-template-keys-parser-client-01/summary.json).

The subsequent diagnostic passes the same outcomes with verification disabled,
16,503 observed hits, bounded worker histories and reconciled kernel CPU.
Across the ten worker records for valid cached edits, median key processing is
10.539 ms, lookup 0.602 ms, restoration 1.715 ms, miss emission 28.800 ms and
capture/insertion 1.183 ms. Ordinary preparation is 40.928 ms.
[Diagnostic](../results/buffered-template-keys-phases-parser-01/summary.json).

Earlier unbuffered diagnostic medians were 8.883 ms for keys and 37.913 ms for
ordinary preparation. These different-time, instrumented runs do not establish
causal regression or speedup. They provide no affirmative support for buffering;
park it without installation or a new end-to-end run. Keep the completed digest
full guard unmeasurable and the adopted runtime unchanged.

Next inspect actual per-function template misses and storage turnover, since miss
emission remains the largest preparation phase. A bounded diagnostic should bind
each attempted function/key, lookup result, insertion charge and emission cost,
then independently reconstruct the existing LRU. This distinguishes capacity
turnover from unseen or changed keys before choosing a new runtime policy. Keep
current identities, memory limits, guest outcomes and strict checking intact.
