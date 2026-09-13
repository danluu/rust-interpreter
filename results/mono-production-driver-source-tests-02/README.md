# Production compiler driver source checks

The original three admission/process tests passed at `71d565f2` (0.046 seconds
reported by unittest). After review identified bootstrap's second source link,
all six tests passed at `d116944a` (0.057 seconds). The added controls cover the
real two-link layout, a foreign checkout target, and unexpected directory
contents. Each run held the canonical workload lock and retained its exact
tested module, tests, child output and completion receipt, and supervisor.

The reviewed plan02 prepare attempt stopped at its 36 GiB entry check with
36,403,642,368 bytes free. It ran zero child commands and created no compiler
checkout. This is an admission failure, with no build or benchmark result.
The original plan and both test histories remain preserved.
