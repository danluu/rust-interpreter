# General interpreter arithmetic and scalar memory improvements

The combined candidate passes the predeclared runtime screen and an additional five-workload confirmation. It specializes scalar loads/stores at ordinary integer widths, replaces shift-count remainder with a mask, and prepares signed operands/comparisons only in operations that use them. No workload names, guest input values or expected results affect the implementation.

| Workload | Interpreter wall change | Interpreter CPU change | JIT wall change |
|---|---:|---:|---:|
| pgrust | -12.67% | -12.62% | -1.25% |
| nushell | -2.71% | -4.12% | -0.29% |
| ruff | -12.68% | -12.73% | +0.27% |
| simd | -12.27% | -13.56% | -0.33% |
| tls | +0.78% | -2.04% | -2.39% |
| allocator | +2.32% | -0.07% | -3.03% |
| fre-forward_middle_hit | -20.49% | -20.52% | -0.23% |
| fre-forward_single | -19.29% | -19.28% | +0.10% |
| fre-forward_range | -17.99% | -18.42% | +0.79% |
| fre-packed-literal-set | -14.61% | -14.90% | -0.91% |
| nushell-type-relations | -5.19% | -7.79% | +0.83% |

Negative changes are faster. These are medians of six paired changes after a warmup pair, with alternating execution order on a shared host. They are descriptive measurements, not confidence intervals. The four tiny SIMD/TLS/allocator/Nushell startup cases should not be treated as precise speedup estimates.

All 308 commands across the final screen and confirmation preserve established stdout, logical instruction count and peak guest memory on identical saved artifacts. Both VMs use the same pinned release compiler and configuration. The confirmation cases were selected before timing and required no material wall/CPU regression (>5% and >5ms absolute median difference) in either engine. All guards pass.

The screen requires at least 10% improvement on pgrust or Ruff, no >5% compute-interpreter wall/CPU regression, and no material JIT regression. The shift-only candidate improved those compute cases about 2.3–2.6%; adding scalar memory specialization improved them about 8.4%. Both failed and were parked. Deferring unused arithmetic preparation is a distinct implementation that raises the combined improvement to about 12.7%; the fixed gates were not changed or retried for an unchanged failed candidate.

Assembly explains the change: the old helper calls software 128-bit remainder before dispatching every binary operation. After masking, it still eagerly prepares signed operands and comparisons; the final implementation moves that work behind opcode/signedness branches. Constant-width scalar accesses retain safe range/read-only checks and a fallback for every other width 0–16.

Correctness: 297 workspace tests pass in debug and 297 in release (one ignored in each). Release tests were split into 255 bytecode tests and 42 dependent-package tests. Native-oracle tests cover all integer widths, high-bit shift counts, signed/unsigned comparisons, divide faults, and every invalid width. Scalar-memory tests cover every size 0–16, all alignments, both arenas, exact boundaries, byte order, empty dangling pointers and rejected stores preserving memory. Existing Python tests and a 12-command runner smoke pass.

This is saved-bytecode execution including VM startup; export, frontend, linking and complete source-edit latency were not measured. The results do not prove unknown-holdout performance. Existing immutable tool 9637b0ac and its historical end-to-end results remain separate. The host had other user-owned work and tight disk space; no unrelated processes, sources or caches were controlled or removed. A new isolated build directory used about a few hundred MiB rather than rebuilding project dependency trees.

The runner records a child receipt inside the wall interval, so tiny-case wall figures include that parent I/O. Child CPU excludes it. Original measured harness snapshots, exact commands, build/test logs, source snapshots, binaries and artifact hashes are retained under the absolute local paths in [summary.json](summary.json). The final runner additionally supports per-case limits and waits for its child even if writing its receipt fails; its smoke is a correctness check, not a timing result.

Reproduce with `scripts/compare_saved_runtime.py`, explicit baseline/candidate binaries, the retained manifest, a fresh output directory and the shared benchmark lock. Do not overwrite an existing run directory.
