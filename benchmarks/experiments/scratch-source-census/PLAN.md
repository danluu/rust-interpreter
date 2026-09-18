# Count additional scratch source/width coverage without changing execution

The adopted memory attribution retains 247/124 payload-load samples in the two
current token captures. Count additional actual load words whose bytes are still
held in x9, using an explicitly enabled test-only observer. The installed VM and
production emitter stay unchanged.

Extend only the observer: record Copy sources before the typed destination
write invalidation, and track exact 1/2/4/8-byte frame ranges. Copy needs matching
low bits only. Load is restricted to eight bytes because narrow loads must zero
extend; unmasked Store captures cannot prove that property. Query after address
handling and only when the adopted production scratch cache still emits a load.
Conservatively clear on the existing reviewed register-clobber/control-transfer
classifier and unknown writes; retain bounded capacity and exact overlap checks.

The observer follows original emitted words, so a counted load still clobbers
its shadow state. This counts directly witnessed opportunities and may miss
cascading opportunities after a real elision. It does not rewrite native code or
predict full-command latency. Whole-operation samples stay separate from samples
on the single candidate load word. Both source/width and existing-destination
origins remain visible in the report.

Run nine scratch observer controls in debug and release, including narrow-bit
limits, aliasing, clobbers, capacity, and unchanged emission on an eight-case
Copy/Load fixture. Run the four memory-part reconstruction controls, then
reconstruct the two closed same-process captures and attribute actual load PCs.
Require full ordinary/scalar native bytes, operation maps and sample accounting
to match. No guest execution or executable publication occurs.

Use the ROOT-only shared target, two Cargo jobs, existing nonincremental/debug
settings, the global lock, max(14 GiB, 8 GiB + twice allocated target) initial
admission and an 8 GiB child floor. Retain failed attempts. Do not clean shared
targets or affect peer processes. Select a production candidate only after
seeing the additional coverage, then qualify semantics and real edit latency.
