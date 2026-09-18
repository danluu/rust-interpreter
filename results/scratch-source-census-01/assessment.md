The observer and complete native reconstruction pass, but the additional sampled coverage is small. Keep this as a possible future component; do not implement or time the source/width extension by itself. The adopted production runtime remains unchanged.

| Capture | Additional static load sites | Whole-operation samples | Actual load-word samples | Generated self samples |
| --- | ---: | ---: | ---: | ---: |
| block | 1532 | 23 | 22 | 1561 |
| exhaustive | 2589 | 2 | 1 | 1231 |

Only 22 / 1 sampled load words are directly covered (1.41% / 0.08% of generated self samples in these windows). Most block coverage comes from four-byte Copy destinations; adding Copy source snapshots contributes just three / one samples across its widths. Thousands of static sites therefore do not establish a useful whole-command gain. The observer follows the original instruction stream and can miss cascading effects of actual elision; neither these counts nor the partial windows predict performance.

Nine scratch controls pass in both debug and release, including exact widths, byte overlap, unknown writes, clobbers and unchanged emission; four memory-part controls also pass. Both complete saved arenas, ordinary functions, scalar bodies and operation maps reconstruct exactly. Queries happen after address handling and exclude loads already removed by the production cache. Narrow Load results remain excluded because matching low bits do not establish zero extension.

The closure verifies 282 frozen source/retained bindings and 25 artifact bindings. No guest command or executable publication occurs. Controllers require experiment source `f04568c8`; main retains the adopted runtime.

Next partition the current native Call/Return paths, including the scalar transaction separately. They account for 409 / 440 generated self samples in the same windows. Extend only diagnostic labels and saved schema-2 reconstruction, verify the original native bytes, then select a mechanism from the current costs.
