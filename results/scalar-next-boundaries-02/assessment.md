# External writes have the strongest remaining structural coverage

The saved-data analysis passes and exactly reproduces the adopted VM's complete
Call/Return partition. No guest or compiler command runs. Both censuses are
closed with 51 source/retained bindings each; the first compared three policies
and the second added the external-write hypothesis.

| Optimistic structural filter | Functions | Block transition + body samples | Exhaustive transition + body samples |
| --- | ---: | ---: | ---: |
| Wider frames/registers/results | 157 | 7 + 4 | 52 + 34 |
| One extra Call layer | 288 | 16 + 43 | 23 + 55 |
| Existing small cycles | 16 | 2 + 3 | 0 + 1 |
| Leaves rejected for external writes | 179 | 40 + 113 | 0 + 1 |

The captures contain 1,561 block and 1,231 exhaustive generated self samples.
These partial, perturbed samples provide coverage bounds, not speed estimates.
Structural filters do not prove effects, aliasing, native eligibility, bounded
iteration counts or admission at runtime. Counts from different policies may
overlap.

The sparse-set update closure contributes 76 block samples to the write bound,
SipHash `c_rounds` 42, and a vector-extension closure 15. Nested-Call opportunities
also include mutating parents, so Call support alone would not admit them.
Wider results chiefly help the exhaustive test; cycles have little coverage.

Next prototype a bounded private store model before native emission. Preserve
ordinary Call replay on any private fault, correct read-after-write and partial
overlap behavior, exact budgets/PC accounting, fresh-frame exclusion and final
store order. Start with fixed-width accesses, a fixed store-log bound and no
Calls/FFI/allocation/cycles. This is broader scalar-memory support, not a special
case for SipHash or this codebase. The failed read-only candidate stays parked.
