Both fresh original token tests pass on adopted VM `6ac4dd9e`. Same-process schema-2 code maps reconstruct exactly, and every generated self sample receives an operation identity. The nine unchanged attribution contracts were reused through exact source/record bindings; four new commands produce two guest captures and two summaries. No performance measurement occurs.

| Capture | Generated self samples | Copy | Load | Call + Return | Scalar body |
| --- | ---: | ---: | ---: | ---: | ---: |
| block | 1561 | 415 | 178 | 409 | 40 |
| exhaustive | 1231 | 242 | 78 | 440 | 114 |

These are partial perturbed three-second windows with normal OS entropy, not matched latency observations or whole-test dynamic weights. Host preparation, memory handling and post-execution reconstruction remain separately reported. The seeded profiles provide static function/operation identity only. Do not compare these sample counts to old captures as a speedup.

Copy/Load and Call/Return remain useful diagnostic targets. First partition the actual memory-emission spans into address, check, register and payload work using the existing observer, retaining exact full-code reconstruction. Choose a bounded mechanism only after that attribution; preserve all strict/fault/budget/alias semantics and real changed-source gates.

The closure verifies 258 frozen source/retained bindings and 56 artifact bindings. Original inputs, code maps, sampler process identities and logs remain retained.
