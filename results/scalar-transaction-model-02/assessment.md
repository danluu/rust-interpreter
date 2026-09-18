# Bounded private stores retain material coverage

All 367 bytecode tests pass in debug and release (15 ignored observers per
profile). The model compares complete active linear/heap memory at VM exit,
including errors, with the project's ordinary interpreter. Stores remain private
until successful Return; reads overlay prior stores in order, and any failure
replays the ordinary Call. Production store admission and native store emission
remain closed. Existing native unit tests still exercise the established JIT.

The source-bound public-artifact census admits 168 store-bearing plans at 211
direct call sites. The exact adopted-VM sample join retains 39 transition and 99
body samples in the block test, out of 1,561 generated samples; exhaustive retains
one of 1,231. Sparse-set update accounts for 76 samples, SipHash rounds for 42,
and vector extension for 15. These are coverage bounds, not speed estimates.
The complete scalar/alias model removes 15 samples from the earlier optimistic
external-write bound. Work budgets remain available.

The closure verifies 318 frozen inputs and 19 retained artifacts. Four commands
finish in 61.49 seconds of setup; no original-project guest or latency comparison
runs. Add explicit branch and non-idempotent rollback controls before starting
the native implementation. Keep the failed first build and main's adopted VM.
