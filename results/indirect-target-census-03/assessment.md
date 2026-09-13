# Indirect-call coverage on the adopted runtime

Both original token tests pass through the explicit main-thread diagnostic.
Their guest memory, entropy consumption, every interpreted/native per-PC count,
native Call/Return counts and generated machine words exactly match the adopted
profiles. This is instrumented coverage evidence, not a performance result.

| Observation | Block boundaries | Exhaustive semantics |
| --- | ---: | ---: |
| Validated indirect calls | 1,025,947 | 843,776 |
| Executed indirect sites | 23 | 21 |
| Calls at monomorphic sites | 1,025,947 | 531,462 |
| Calls at sites with at most two targets | 1,025,947 | 843,768 |
| Calls at sites with at most four targets | 1,025,947 | 843,776 |
| Callee entry already native | 1,025,927 | 843,753 |
| Caller continuation already native | 1,025,947 | 843,776 |
| Existing VM local-argument proof | 0 | 0 |

The largest block site is hashbrown find_inner:948,377 calls, one target and
only its first entry unprepared. The largest exhaustive site is Prefilter::find:
312,300 calls across two targets. No target order was recorded; these totals do
not establish an eviction policy's hit rate or a wall-time improvement.

Proceed with a general native indirect transition using exact, immutable
signature/layout metadata and the existing native frame protocol. Full128-bit
handle validation, bounded indices, exact argument/result sizes, all frame and
memory limits, fault order and instruction budgets remain mandatory. Cold or
unavailable code returns to the VM. No workload IDs or profiled target choices
enter the implementation. A bounded target specialization is a later comparison
if dynamic layout costs remain material; start with the simpler static code
ownership and one native transition per bytecode PC.

Ordinary VM builds contain no observer hook or runtime switch. The explicit
indirect-target-observer Cargo feature builds a separate main-thread executable.
The earlier libtest observer passed417 tests/profile but its first replay was
correctly rejected by the main-thread-only entropy helper (exit86); no guest
case completed. Its build and incomplete replay remain recorded, along with the
original report-field compilation error and occupied-lock admission. The revised
observer passes417 tests/profile,10 ignored diagnostics, and both exact replays.
No entropy-helper check was weakened and no completed guest replay was repeated.
