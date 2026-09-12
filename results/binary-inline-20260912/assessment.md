# Inline the existing integer operation helper

The candidate passes its fixed runtime screen and five additional workload checks
against the qualified complete-scalar-memory-inline VM (`d2a2597`, merged as
`ad31f94`). It adds only `#[inline(always)]` to `binary()`. The method body,
integer widths, overflow results, faults, operand checks and write ordering are
unchanged. This also affects the helper's JIT constant-folding callers; the
process-runtime regression checks cover both engines.

| Workload | Interpreter wall change | Interpreter CPU change | JIT wall change |
|---|---:|---:|---:|
| pgrust | -3.03% | -2.95% | -0.94% |
| nushell | -1.14% | +1.13% | +1.20% |
| ruff | -5.80% | -5.78% | -1.54% |
| simd | -1.34% | -1.07% | +1.89% |
| tls | +5.64% | +4.56% | +1.09% |
| allocator | -0.65% | +1.80% | -1.49% |
| fre-forward_middle_hit | -4.29% | -4.33% | -0.04% |
| fre-forward_single | -7.55% | -7.55% | +0.44% |
| fre-forward_range | -7.51% | -7.91% | -0.24% |
| fre-packed-literal-set | -2.77% | -2.80% | -0.64% |
| nushell-type-relations | -2.77% | -3.09% | +1.11% |

Negative changes are faster. Values are medians of six alternating paired
changes after a warmup pair. Ruff wins all six measured pairs, pgrust five, and
each additional workload all six. The short TLS interpreter case regresses
5.64% (0.171 ms difference between separate wall medians); the other startup
controls are also noisy. These shared-host observations have no confidence
intervals. JIT passes regression guards; no general JIT gain is claimed.

The prospective screen requires at least 5% interpreter wall improvement on
pgrust or Ruff, neither compute case regressing more than 5% wall/CPU, and no
JIT wall/CPU regression exceeding both 5% median paired change and 5 ms difference
between marginal medians. The five additional cases use that material guard in
both engines. All gates pass. All 308 public comparison commands, including
44 warmups, preserve outputs, logical instruction counts and peak guest memory
on unchanged frozen artifacts.

All 297 workspace tests pass in debug and release (one ignored). The Python
suite passed all 21 tests at the baseline; this optimization changes no Python
code. All 280
native-oracle commands, including 40 warmups, preserve expected native Rust
outputs across signed/unsigned widths 8/16/32/64/128 in both engines. Narrow
checksums supplement the existing boundary, fault and aliasing tests. All 588
comparison commands pass, including 84 warmups.

Assembly removes the integer helper call and successful result-buffer round
trip. Common bitwise paths write guest registers directly; checked register
accesses remain. Compiler-runtime 128-bit division/remainder calls and some
interpreter-state reloads remain. The pure interpreter grows from 12,288 to
14,656 bytes including alignment; its fixed frame shrinks from 1,232 to 1,216
bytes, and the helper's separate 48-byte frame disappears on common paths.
The executable grows by 16,464 bytes. These are code-generation observations,
not a percentage attribution of the measured gains.

This qualifies saved-bytecode process runtime including startup. It does not
measure build latency, full edit/build/test improvement or unknown holdouts.
Gains are relative to the immediately preceding qualified VM, not cumulative
estimates from earlier experiments. Subsequent optimization work targets build time.

[Predeclared plan](predeclared-plan.md), [screen](screen-summary.json),
[screen gate](screen-assessment.json), [confirmation](confirmation-summary.json),
[confirmation gate](confirmation-assessment.json),
[native-oracle checks](native-oracles-summary.json),
[code generation](code-generation-review.md), [provenance](qualification.json).
Exact snapshots, immutable binaries, commands, logs and harness/disassembly
copies remain under the isolated worktree's `.work/perf-general-20260912`.

Integration with upstream `1b57dae` preserves all qualified Rust source, Cargo configuration, the toolchain and measured comparison harness. Upstream documentation and status-generation changes remain included.
