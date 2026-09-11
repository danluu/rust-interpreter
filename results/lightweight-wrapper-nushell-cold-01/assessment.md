# First of six balanced cold histories

The first predeclared Nushell history completes and verifies all nine primary
commands, three independent checks and six identical paired artifacts. All
fourteen original type-relation tests and the deliberately wrong edit retain
their expected outcomes. The pinned source is restored byte-for-byte. All ten
frozen input hashes and six compiler-wrapper traces verify.

Initial order is native, baseline, candidate. Tools remain 78e60cdd and c341296c
with the identical VM, ordinary JIT, matched leaf inlining and the same std-MIR.
Native uses eighteen jobs/O0/incremental/default test concurrency; custom
commands use four jobs. Cold means a fresh target/cache namespace, excluding
toolchain installation, dependency downloads and prebuilt std-MIR setup. Other
workloads and OS caches were left alone.

| Cold command | Wall seconds | Child CPU seconds |
| --- | ---: | ---: |
| Native | 37.567 | 246.081 |
| Baseline | 61.439 | 179.987 |
| Lightweight wrapper | 61.539 | 180.818 |

The candidate/baseline cold wall ratio is **1.0016210970** (+0.162%); the CPU
ratio is **1.0046207955** (+0.462%). This first history shows no cold-command
benefit. It is one of six required samples, not a retention decision. The
other five fixed permutations remain required, with the original median cold
improvement threshold of at least 5% and warm regression guard unchanged.

The API-edit command takes 11.848s native, 5.281s baseline and 5.143s candidate.
This one pair remains part of this cold experiment; it is not added to the two
completed fifteen-cycle warm comparisons. Source-state artifact hashes match
the initial-history qualification; this does not resolve the previously seen
post-revert allocation-history difference.

Supervisor 21379/controller 21382 and verification supervisor 25899/worker25910
finished with status 0. [The verification](verification.json) checks full
command/source/artifact controls, and [frozen-input evidence](frozen-inputs.json)
records the restored source hash and wrapper identities. [Raw timings](summary.json)
retain full precision. Cache archival occurred before the run, outside its
timers; the next history will use new target/cache identities.
