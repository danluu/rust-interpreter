# Native continuations and transition counters

Both adopted captures reconstruct exactly, all1101/1305 functions. The observer
passes414 bytecode tests in each build profile. A separate proposed layout type
shows a32-bit code offset could fit at byte44 without growing the48-byte host
Frame; production Frame and emission are unchanged. Resume instruction indices
are explicitly converted to byte offsets. The failed initial test is retained.

All66,403,920 /70,368,216 profiled native Calls have a compiled internal next-PC
resume target. Static sites include3050/3595 eligible Calls and32 unsupported
continuations in each capture; those unsupported sites have zero hits in these
profiles. No executed functions are omitted. This does not assign individual
Returns to callers: native Returns are67,430,947 /71,213,273, exceeding native
Calls. Frames entered by the VM still need the original lookup path.

Return dispatch retains35/31 generated-PC samples. Caching an offset would add
199,198,712 /210,208,250 weighted immediate/store words at Calls, before any
saved Return work. Defer that more intrusive relocation/frame change pending a
stronger composition case; full eligibility alone does not establish a gain.

Exact three-word cursor-counter updates account for27/32 Call samples and5/13
Return samples:32/1651 (1.94%) and45/1439 (3.13%) generated samples in total.
Their typed update counts exactly match the existing native Call/Return totals.
There are no ambiguous samples. These windows are partial and perturbed under
ordinary entropy, separate from the bound-entropy profiles used for weights.
Weighted emitted words are not retired instructions or a latency prediction.

Next prototype: retain the native Call/Return counters in caller-saved SIMD
registers across internal native edges, loading/publishing them at every VM
boundary. Preserve wrapping arithmetic, exact counters, all zero-progress/fault/
TLS/budget paths, float/copy/register-clobber contracts and ABI. Compare this
bounded mechanism, potentially with already-qualified successor-live spilling,
against the adopted tool. Account for extra external-entry/exit code and capacity
before timing. Do not include branch-based arena selection or the failed budget
fusion. No new runtime implementation or benchmark exists yet.

The census completed both reconstructions before its final report write failed
because the result directory was missing. The separate attribution-02 step
created that directory and retried only failed attribution. Both original
reconstructions, their receipts and the failed outer terminal are retained.
No guest execution or executable-code publication occurred in this diagnostic.
