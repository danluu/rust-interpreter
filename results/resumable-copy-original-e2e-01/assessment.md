The original-baseline comparison passes both predeclared primary gates. Source `aa2f6ea` / tool `0e94d6d8` uses resumable calls and persistent registers; original `b2aa6efe` uses ordinary JIT. No runtime default changes.

| Workload | Native median | Original JIT median | Candidate median | Paired wall change | Paired CPU change |
| --- | ---: | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.653s | 2.465s | 1.913s | -21.82% | -21.95% |
| token-phrase | 2.012s | 6.613s | 4.418s | -33.09% | -33.29% |

These are complete source-edit/build/test commands: three cycles of five original edits, fifteen pairs per workflow. The median paired ratios are computed within each edit; they are not ratios of the separate medians. Folded meets the required 10% wall reduction and token the required 20%, with lower child CPU for both. Native uses eighteen jobs, O0/incremental and default libtest concurrency; both custom modes use four jobs. Installed tools and std-MIR setup are excluded and separately reported. No OS-cache coldness or fastest-native claim is made.

Verification covers 126 primary commands, 42 independent check commands, 30 edited pairs and 84 artifact snapshots. Original assertions, deliberately wrong edits, corresponding-mode artifact equality, frozen corpus inputs, exact installed tools and all pinned source restorations verify. Cross-cycle artifacts are not all identical; the existing layout variation is preserved. Native Cargo remains faster on both compute workloads.

The [matched-runtime comparison](../resumable-copy-e2e-01/assessment.md) separately isolates the new copy implementation and measured a 15.14% token gain. This original-baseline comparison measures the combined runtime direction, including earlier resumable calls/registers/clearing changes. It does not attribute the full gain to copying.

Fresh native/TLS/fre correctness and the seven held-out workflows remain required before retention. Older coverage does not transfer. See [exact gates and stage medians](gate-evaluation.json) and [verification](final-verification.json).
