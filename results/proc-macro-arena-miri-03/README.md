# Isolated Miri qualification of actual Arena03

The runner uses the official pinned Miri component, the installed matching
nightly's read-only rust-src, and a fresh workspace-owned Cargo home, temporary
build directory, and Miri sysroot. Cargo is offline and has one build job.
Only the 31 pinned lockfile index entries and the 12 Darwin-selected package
archives (plus registry configuration) are copied from the existing user cache.
No user cache, installed toolchain, or compiler source is modified.

`result.json` records the actual outcome. Setup must pass before the unchanged
actual Arena wrapper runs under the default alias checker and Tree Borrows.
Each command retains passed environment, PID, start and waited closure, raw
output, limits, and source hashes. The canonical lock is inherited by children.
Fresh admission requires 16 GiB free; capacity observations are posthoc checks,
not a claim that the runner can halt a running child without a signal. It never
sends signals. The planned workspace budget is 4 GiB and observed free-space
floor is 8 GiB. Compiler integration, interner tests, and benchmarks are outside
this run. The publication manifest excludes itself.
