# Remaining JIT preparation in real edits

Seven controls and95retained adopted-baseline edit receipts pass. No guest or
compiler was run. The original one-worker private history remains included;
the first observer failure is retained. Durations below are medians of the
per-receipt quantities, so columns must not be added or divided to derive a
new statistic. Compiler intervals overlap across workers and are elapsed
intervals, not on-CPU time, cache hit rates or predicted wall savings.

| History | Command s | Compiler sum ms | Largest worker compiler ms | Constructor sum ms |
| --- | ---: | ---: | ---: | ---: |
| token | 3.888 | 258.06 | 149.59 | 68.67 |
| folded | 1.600 | 72.76 | 52.27 | 15.59 |
| pgrust | 0.546 | 4.70 | 2.40 | 0.45 |
| rg-aot | 0.280 | 2.48 | 2.48 | 0.31 |
| nushell | 5.650 | 15.07 | 7.75 | 2.05 |
| nushell-parser-incremental | 1.690 | 213.92 | 124.63 | 45.06 |
| token-recent | 3.766 | 255.00 | 147.51 | 65.61 |

PreparedJit already retains native code and analyses in each worker. The
cumulative published code is counted once per owner:26.7MB for token and24.6MB
for the full parser, not once per test. The parser has a median two declined
function owners under the fixed16MiB per-worker arena; a reuse proposal must
preserve bounded admission and interpreter fallback.

Cross-process native reuse is worth a bounded feasibility study for parser
and fre, but it has little room to improve these pgrust/private/type-relation
commands. Even fre's aggregate compiler interval is only6.6–6.8% of the complete
command, with substantial overlap. Nushell type-test compiler sums exceed its
execution wall time, directly showing why these sums cannot be called savings.

Next census typed function identities across the actual saved edit/revert
histories. Separate unchanged local bodies from unchanged direct-callee
dependencies and program-wide emission inputs. Count global invalidation and
identity shifts explicitly. Unchanged bytecode is only a necessary condition;
native relocations, assertion identities, scalar eligibility, finite analysis
budgets and code capacity still need a complete reuse contract. Measure cache
keying/I/O/population costs inside any later real workflow. No cache is admitted
or implemented by this audit. Compiler/Cargo work stays with its owner.

The first two evidence-closing attempts timed out45seconds on the shared lock.
Closure03 completed under60841/60866 once the lock became available, verifying
141frozen inputs,12source bindings and136evidence files against the original
successful audit terminal33033/33036. No receipt or control was rerun.
