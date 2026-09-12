# Integer shift mask screen

Candidate: mask shift counts using the validated power-of-two integer width.
Baseline: 3e44055 interpreter; current origin/main 448825f has identical Rust sources.
Both binaries use the same pinned release compiler and build configuration.

Gates declared before timing: all bytecode crate debug/release tests pass;
all six saved public artifacts return their established results with identical
logical instruction counts and peak guest memory in interpreter and retained JIT.
Six alternating paired repetitions after one warmup pair per case/mode.
Require >=10% median paired runtime gain in at least one of the two compute cases
(pgrust, Ruff), no >5% wall/CPU regression in either compute interpreter case,
and no material JIT regression (>5% and >5ms absolute median difference).
Short cases are startup/correctness guards; no speedup claims from their noisy ratios.
This screen measures saved-artifact execution, not export/build or unknown holdouts.
No benchmark-specific code or changed bytecode.
