# Store-log primary fails; candidate parked

All 40 changed-source commands retain the original 12 tests, expected wrong-edit
failures, five valid edited pairs, bytecode/catalog identity and source restoration.
Normal OS entropy, two Cargo/prepared workers and the 16 MiB arena are unchanged.

| Measure | Candidate / adopted baseline |
| --- | ---: |
| Paired median wall | 0.976436059 |
| Paired median child CPU | 0.996166622 |
| Maximum absolute A/A wall deviation | 0.046293273 |
| Maximum absolute A/A CPU deviation | 0.016088033 |
| Wall ratio plus A/A deviation | 1.022729332 |
| CPU ratio plus A/A deviation | 1.012254655 |
| Candidate / ordinary native wall | 1.502191479 |

The 2.36% lower wall median does not clear 4.63% observed baseline variation.
The gate fails. Park tool 5b86b3ab; do not repeat it or start the larger project
and parser histories. Main retains df4006e0. Closure verifies 1,670 evidence
files and 56 retained artifacts.

Descriptive stage medians are Cargo -44.6 ms and execution -71.3 ms. They are
nested/nonadditive, vary with unchanged frontend work, and establish no causal
runtime speedup. The candidate's bytecode/strict/original-profile qualification
remains valid correctness evidence, not adoption evidence.

Next inspect live scalar-register pressure and spill traffic in the exact saved
bodies. The backend reserves only four registers for scalar values. Quantify
which successful paths could benefit and the extra save/restore cost before
changing the register pool. Preserve the parked store-log and earlier failures.
