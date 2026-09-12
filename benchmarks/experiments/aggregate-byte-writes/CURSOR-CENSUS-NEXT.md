# Split the observed cursor cost before changing its ABI

The fresh exact-artifact profiles attribute 14.19% of token and 11.31% of folded
thread self samples to direct 64-bit loads/stores through x19. This is the
resumable cursor, but its fields have different semantics. Do not treat all of
this share as instruction-budget work or a speedup forecast.

Use the six existing code dumps and samples; no new benchmark, guest execution
or runtime change is needed. Decode only the exact load/store class already
recognized by `attribute_generated_sample.py`. Split its unsigned immediate
byte offsets by the pinned `State` / `ResumeCursor` layout assertions, preserving
load versus store and entry kind. Bind the source layouts to each capture's
frozen source hashes and immutable VM. Other addressing modes stay unclassified.

Reverify each original attribution. Multiple PCs grouped by the sampler count
once; assign a field only when every PC agrees on field and direction. Preserve
ambiguous groups and reconcile all counts with the existing cursor category.
Reject foreign registers/widths and unknown layout offsets as field evidence.
Do not infer a value's lifetime, observability or safety from a sampled offset.

Choose any ensuing ABI experiment only after this split. Preserve exact
instruction budgets, profiling semantics, call/return counters, frame extents,
fault order, Rust fallback and all exit paths. Account for any physical-register
pressure or added transition spills in the actual end-to-end comparison.
