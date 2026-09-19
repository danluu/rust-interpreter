# Adopted runtime still retires substantially more instructions

The three fresh counter API controls and all twelve original assertion processes
passed and independently closed. Both modes use the exact restored fre source
state from the closed heap-layout primary, with the adopted df4006 runtime.
No compiler, source edit, candidate, profiling, or entropy injection was used.

| Original assertion | JIT/native retired instructions, median (range) | JIT/native cycles, median (range) |
| --- | --- | --- |
| Block boundaries | 3.5647 (3.5623–3.5648) | 2.3664 (2.3529–2.4091) |
| Exhaustive byte semantics | 5.2494 (5.2464–5.2502) | 3.6374 (3.6158–3.6511) |

Native cycles/instruction are approximately 0.256 for block and 0.225 for
exhaustive; JIT values are 0.169–0.173 and 0.156–0.157. The JIT's lower aggregate
cycles/instruction does not support blaming its entire excess cost on stalls.
Reducing executed work remains a useful direction, although aggregate counters
cannot identify which instruction sequences are removable or exclude local
cache/branch problems.

Counts include each target's entire process lifetime: native libtest setup or
custom bytecode loading, analysis and JIT preparation plus guest execution.
They exclude the parent counter launcher and Cargo. These are ordinary-entropy
assertions, not exact entropy pairs, phase-specific counters, or changed-source
build/run timings. Three pairs are diagnostic evidence only. All pairs are
retained; no retry or selection was performed.

The old 7.13 instruction ratio used runtime 49746a22. The fresh 5.25 exhaustive
ratio is the relevant current observation; differences in artifact/runtime and
measurement occasion prevent treating their difference as a new optimization
speedup. No defaults change. Any next candidate still needs the existing
changed-source primary and all downstream guards.
