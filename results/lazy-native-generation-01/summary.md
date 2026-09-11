# Lazy native function generation

The custom JIT now prepares a function when execution first enters it. The
retained-program replay passes **381 of 382 ordinary fre tests**, preserving all
320 previous passes and adding61. All382 fresh native processes pass. Seven
original ignored tests remain ignored. The one guest failure reaches the existing
100,000-live-allocation limit; an isolated probe confirms that guard, separately
from byte memory or native-code capacity.

The native-code cap stays **16 MiB**. The largest successful replay commits
**10,092,216 bytes**; none of these successful real runs declines a function for
code capacity. Lower-budget regression tests exercise the own-interpreter fallback.
The first formerly code-limited test compiles875 of5162 functions and uses4,241,540
native bytes, preserving6,636,088 logical instructions. Native emission and guest
interpretation use this project's engine.

All130 bytecode tests, both23,502-command native differential configurations,
245 TLS/callback checks, and the targeted compiler/runtime gates pass. Tests check
delayed compilation order, stable earlier entries, staged assertion identities,
recursion, indirect calls, exact budgets, faults, profiles and unused invalid
bytecode. Preparation occurs at calls and TLS transitions without a new readiness
check in the instruction dispatch loop.

This replay uses the already collected, hash-verified MIR3/inline8 programs and
verified native executable from the pinned fre revision. It validates every
program in the candidate VM and runs native/guest tests in fresh processes from
the repository root. It does not repeat frontend collection or rebuild the native
control. The bytecode encoding and exporter lowering logic are unchanged. Runtime
coverage is distinct from a source-edit performance result or whole-application
support. Two production-edit comparisons are complete; broader qualification remains pending.

| Production-edit workflow | Previous JIT median | Lazy JIT median | Native median | Paired command change | Wins vs previous / native |
|---|---:|---:|---:|---:|---:|
| [TLS, MIR3 with larger inlining](../paired-lazy-native-forward-anchored-tls-01/summary.md) | 1.249 s | 1.183 s | 1.595 s | −1.022 ms | 3/5 / 5/5 |
| [Folded trie, ordinary MIR3](../paired-lazy-native-folded-literal-trie-01/summary.md) | 3.861 s | 3.801 s | 2.185 s | −44.368 ms | 4/5 / 0/5 |

All fourteen original/wrong-edit/valid-edit artifact pairs are byte-identical.
Each mode rejects the wrong production edit, then runs the same original tests
following five valid production edits. The paired median, rather than subtraction
of independent medians, governs the comparison. TLS is effectively flat against
the previous JIT; its five native wins retain the earlier MIR-tuning benefit.
Folded-trie's command saving comes from Cargo: its execution stage regresses by a
paired median of26.170 ms while Cargo improves by68.534 ms. No broad speed gain is
established. All cold costs and individual pairs remain in the linked reports.

Keep this as an experimental capability improvement. Inspection of the built VM
shows that a cached function check still enters two host helper calls, including
a240-byte stack frame in `ensure_function`, before returning. The next candidate
will keep that common check inline and move first-compilation work into a separate
cold helper, then repeat real edited-command comparisons. That overhead is a
hypothesis for the execution regression, not an established causal attribution.
