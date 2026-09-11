# Balanced cold history 2 of six

All nine primary commands, three independent checks, six paired artifacts,
ten frozen input hashes and six wrapper traces verify. The pinned source is
restored byte-for-byte. Original fourteen tests and wrong-edit controls pass.

Initial order: `candidate,baseline,native`.

| Cold mode | Wall seconds | Child CPU seconds |
| --- | ---: | ---: |
| native | 41.589 | 277.710 |
| baseline | 62.435 | 185.099 |
| candidate | 61.617 | 179.875 |

Candidate/baseline cold ratios: **0.9868934347 wall**, **0.9717771801 CPU**.
This is one predeclared sample, not a retention decision. All six histories
and the original cold/warm criteria remain required. Edited observations in
this run are not added to the completed fifteen-cycle warm comparisons.

Tools remain 78e60cdd/c341296c with identical VM, ordinary JIT, matched leaf
inlining and std-MIR. Native uses eighteen jobs/O0/incremental/default test
concurrency; custom uses four jobs. Cold excludes installation, downloads
and prebuilt std-MIR setup. No OS caches were cleared or other work controlled.

[Full precision and provenance](cold-observation.json), [workflow checks](verification.json),
and [frozen inputs/source restoration](frozen-inputs.json) are preserved.
