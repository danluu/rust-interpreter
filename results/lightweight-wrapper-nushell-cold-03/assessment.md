# Balanced cold history 3 of six

All nine primary commands, three independent checks, six paired artifacts,
ten frozen input hashes and six wrapper traces verify. The pinned source is
restored byte-for-byte. Original fourteen tests and wrong-edit controls pass.

Initial order: `baseline,candidate,native`.

| Cold mode | Wall seconds | Child CPU seconds |
| --- | ---: | ---: |
| native | 44.295 | 298.766 |
| baseline | 66.222 | 195.943 |
| candidate | 66.785 | 200.375 |

Candidate/baseline cold ratios: **1.0085092329 wall**, **1.0226163989 CPU**.
This is one predeclared sample, not a retention decision. All six histories
and the original cold/warm criteria remain required. Edited observations in
this run are not added to the completed fifteen-cycle warm comparisons.

Tools remain 78e60cdd/c341296c with identical VM, ordinary JIT, matched leaf
inlining and std-MIR. Native uses eighteen jobs/O0/incremental/default test
concurrency; custom uses four jobs. Cold excludes installation, downloads
and prebuilt std-MIR setup. No OS caches were cleared or other work controlled.

[Full precision and provenance](cold-observation.json), [workflow checks](verification.json),
and [frozen inputs/source restoration](frozen-inputs.json) are preserved.
