# Query available x9 values at Copy loads

Fresh exact memory subparts identify 95/72 samples at eight-byte Copy data loads.
The earlier scratch observer only queried Load operations; Copy-to-Copy chains
remain unmeasured. Extend the test-only observer to query immediately before a
non-forwarded eight-byte Copy load, after all original source/destination
address handling. Keep a separate Copy hit vector so older Load reports retain
their meaning. No instruction substitution or production emission change.

Use existing exact active-frame range facts, at most 16 snapshots, and the
reviewed conservative x9 instruction classifier. Keep every overlap/unknown
write, possible x9 clobber and control-transfer invalidation. Only a preceding
real load/store/copy can capture bits. Do not retain a fact merely because the
same value would be reloaded; the unchanged machine instruction clobbers it.

Run six scratch controls, four memory-partition controls, two Python join controls
and exact reconstruction of both saved scalar captures. Require unchanged bytes,
coarse/fine spans, assertions, resume identities and no executable publication.
Join candidate sites to both complete Copy spans and their exact load subparts.
Report static sites separately from partial captured samples; no frequency or
entropy-based extrapolation. Low coverage parks the hypothesis without a timing
screen. Material coverage only authorizes a separately qualified implementation.

Use the same source root and shared target, two Cargo workers, global lock,
14 GiB/max(8 GiB+2x allocated target) admission and 8 GiB child floor. Preserve
the original samples, artifact bytes, strict checking and all end-to-end gates.
