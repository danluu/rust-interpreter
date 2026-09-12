The isolated CLI passes 23 recorded commands. Nine successful engine cases compare serialized legacy interpreter, legacy JIT and scalar interpreter artifacts against native Rust for zero, an ordinary input and wrapping overflow. Scalar profile counts and instruction budgets agree exactly; unsupported scalar JIT, invalid registers, truncated files and oversized entry arguments are rejected.

The underlying interpreter has passed 305 debug/release workspace tests. This CLI-only change adds artifact loading and dispatch; it preserves the original version-5 execution route. No runtime was published and no performance comparison ran. Native scalar execution, caller value operands and compiler promotion are the next milestones.

[Command and binary evidence](summary.json), [terminal process receipt](execution.json).
