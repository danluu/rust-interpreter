# Preserving identical executables on macOS

Same Cargo binary with flag off/on; unchanged source, zero rebuilt artifacts, alternating order. This measures no-op workflows, not body edits.

Seconds, median of three observations per condition. Feedback includes build, edit-validation launch, and a smoke workload. These are no-op comparisons on the shared Apple Silicon host.

| Project | Backend | Control feedback | Preserve feedback | Ratio | Control / preserve build |
|---|---|---:|---:|---:|---:|
| rg-aot | llvm | 0.273 | 0.075 | 3.6x | 0.072 / 0.071 |
| rg-aot | clif | 0.292 | 0.080 | 3.7x | 0.073 / 0.075 |
| fre | llvm | 0.342 | 0.104 | 3.3x | 0.091 / 0.093 |
| fre | clif | 0.466 | 0.108 | 4.3x | 0.091 / 0.093 |
| pgrust | llvm | 3.660 | 0.621 | 5.9x | 0.631 / 0.610 |
| pgrust | clif | 5.669 | 0.644 | 8.8x | 1.168 / 0.628 |
| ruff | llvm | 1.268 | 0.216 | 5.9x | 0.195 / 0.203 |
| ruff | clif | 3.615 | 0.238 | 15.2x | 0.195 / 0.216 |
| nushell | llvm | 4.958 | 0.387 | 12.8x | 0.328 / 0.357 |
| nushell | clif | 5.739 | 0.380 | 15.1x | 0.327 / 0.347 |
