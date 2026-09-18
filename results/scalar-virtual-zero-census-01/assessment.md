The virtual-zero admission experiment is parked. All four focused controls pass
in debug and release, including 96 reference-interpreter comparisons per
profile. The census admits 15 additional confined leaves and finds one direct
callsite, but neither current capture contains a sample in their Call/Return
transitions. No production policy change or performance screen follows.

The scan examines all 5,468 functions. Strict admission uses 1,496,863 of its
256-million work units; the relaxed scan uses 16,459, so neither exhausts its
budget. All 15 functions pass scalar lowering and offline native emission in
both profiles. They were rejected only for local reads before writes. Existing
scalar values can model their zeros, but this establishes no useful coverage
of the observed workload cost.

The tests retain confinement, bounds, effects, widths, cycle rejection and work
limits, and compare padding, conditional writes, values, instruction counts and
per-PC profiles with the reference VM. No original-project guest executes and
no executable code is published. Production memory-plan admission is unchanged.

The closure verifies 301 source/retained bindings and 18 artifacts against
source `e20a46e6`. The partial perturbed current captures still account for all
1,561 / 1,231 generated samples and their prior fine protocol partition. Zero
sample coverage is a prioritization result, not proof that these functions can
never matter. The diagnostic Rust source remains on the experiment branch;
these controllers require that source.

Next join current ordinary call targets to their frame shapes and strict scalar
declines. Earlier initialization and bounded-tree experiments already found
limited coverage or failed timing; preserve those outcomes before choosing a
new mechanism for the remaining frame and argument/result costs.
