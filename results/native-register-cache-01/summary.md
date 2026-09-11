# Native temporary register cache

The register cache wins 29/40 completed production-edit commands against its parent, 106eef, and 29/40 against standard native Cargo. 8/8 planned workflows are complete. The exact measured source is integrated as an experimental runtime improvement.

The custom AArch64 emitter keeps one dynamic 128-bit value in caller-saved x5/x6. It spills values needed after eviction or at exits and clears the cache before medium copies reuse those registers. Guest bytecode, block boundaries, instruction budgets, frame initialization and call handling are unchanged. Strict rustc frontend checks remain enabled.

All 151 bytecode tests pass, including eight new pressure, aliasing, branch, budget, fallback and copy tests. The complete folded profile is identical. Broader gate records are linked in the JSON report.

| Workflow | Native / baseline / candidate median command (s) | Paired command change (ms) | Execution change (ms) | Wins vs baseline / native |
|---|---:|---:|---:|---:|
| [folded-literal-trie](../paired-native-register-cache-folded-literal-trie-01/summary.md) | 2.106 / 2.980 / 2.854 | -157.2 | -175.8 | 5/5 / 0/5 |
| [forward-anchored-tls](../paired-native-register-cache-forward-anchored-tls-01/summary.md) | 1.724 / 1.213 / 1.134 | -67.2 | -66.8 | 5/5 / 4/5 |
| [pgrust-sha1-inline8](../paired-native-register-cache-pgrust-sha1-inline8-01/summary.md) | 0.769 / 0.934 / 0.817 | -98.9 | -109.5 | 5/5 / 0/5 |
| [pgrust](../paired-native-register-cache-corpus-pgrust-01/summary.md) | 0.676 / 0.514 / 0.506 | -6.6 | -7.5 | 4/5 / 5/5 |
| [nushell](../paired-native-register-cache-corpus-nushell-01/summary.md) | 0.625 / 0.444 / 0.460 | +8.1 | +0.1 | 2/5 / 5/5 |
| [rg-aot](../paired-native-register-cache-corpus-rg-aot-01/summary.md) | 0.540 / 0.203 / 0.197 | -7.0 | +0.4 | 3/5 / 5/5 |
| [ruff](../paired-native-register-cache-corpus-ruff-01/summary.md) | 5.593 / 2.979 / 3.006 | +30.5 | -1.3 | 2/5 / 5/5 |
| [nushell-type-relations](../paired-native-register-cache-corpus-nushell-type-relations-01/summary.md) | 14.800 / 7.521 / 6.781 | -740.5 | +0.7 | 3/5 / 5/5 |

The comparisons edit production code and run unchanged original assertions. Every mode rejects the deliberate wrong edit. All paired artifacts match the corresponding retained artifacts. Independent medians and median paired differences need not agree. Five pairs per workflow limit conclusions.

All fifteen folded-trie, TLS and SHA-1 commands improve against the parent. Native still wins every folded-trie and SHA-1 pair. Short Nushell and Ruff commands regress by paired medians of 8 and 30 ms; execution is nearly flat. Larger Nushell improves by 740 ms, with a 756 ms Cargo-stage saving and effectively flat execution. Its identical exporter does not establish a causal explanation for that Cargo variation.

The private workflow completed all 21 timed commands before an aggregate-report audit raised a missing-field error. A separate local audit recovered the summary without rerunning timings, verified the private raw assertions and artifacts, and emitted aggregate results only. The final large Nushell wrapper used an 11.5 GiB startup disk reserve instead of 12 GiB; benchmark commands were unchanged and disk usage was monitored through normal completion.

| Workflow | Native / baseline / candidate cold command (s) |
|---|---:|
| folded-literal-trie | 7.761 / 7.486 / 8.054 |
| forward-anchored-tls | 7.208 / 5.808 / 5.583 |
| pgrust-sha1-inline8 | 0.917 / 0.919 / 0.801 |
| pgrust | 0.916 / 0.548 / 0.533 |
| nushell | 22.643 / 22.559 / 21.651 |
| rg-aot | 4.321 / 2.850 / 2.852 |
| ruff | 60.344 / 27.945 / 27.141 |
| nushell-type-relations | 70.345 / 68.600 / 64.133 |

Cold samples use empty per-mode Cargo targets with tools and std-MIR prepared beforehand; filesystem caches are not reset.

Six alternating same-artifact runtime pairs per case:

| Case | Paired change (ms) | Wins |
|---|---:|---:|
| folded (jit) | -148.7 | 4/6 |
| sha1 (jit) | -107.5 | 6/6 |
| tls (jit) | -63.4 | 6/6 |
| pgrust-interpreter (interpreter) | +1.0 | 2/6 |

The folded runtime series retains both initial regressions (+407 and +101 ms); no samples were discarded. The interpreter control is effectively flat. Runtime measurements are a filter, not the development-loop result.

The typed compile-only observer reproduces both measured native code sizes. Across the identical folded trace, generated register-array loads fall from 1,161,857,638 to 189,948,735 and stores from 2,178,397,924 to 1,461,031,200. These are emitted LDR/STR instructions weighted by successful block counts, excluding guest-memory operations and hardware cache behavior. They are not CPU timing or DRAM-traffic measurements.

All 47,004 native differential commands and 245 TLS checks pass. Replay of 389 exact retained fre artifacts preserves 381 passes, one identical allocation-capacity failure and seven ignored tests; 382 fresh native controls pass. Every passing JIT body has zero declined functions. A fresh full build reproduces both measured tool binaries exactly.

The fre replay records 54 bodies with cross-process statistic differences. Repeated unchanged baseline runs also vary while consuming host randomness. The controlled-input diagnostic compares those same 54 bodies under two explicit RNG inputs in isolated builds; the production RNG and JIT emitters remain unchanged. Its result is recorded below.

Whole applications, arbitrary OS/FFI calls, guest threads and native unwinding remain unsupported. No broad warm-build improvement is established.

All 108 controlled-input pairs (216 fresh processes) match original assertion outcomes, instruction counts, native entries and sparse executed per-PC/block counts exactly. Each executes the mocked RNG and has zero declined functions. These are correctness diagnostics, excluded from all performance measurements; two inputs do not establish universal trace equality.
