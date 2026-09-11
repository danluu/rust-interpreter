The native-copy experiment passes its predeclared comparison against the preceding VM. Token improves **15.14% paired wall time** and **15.28% child CPU**. Folded changes **+1.06% wall / +0.54% CPU**, within the 5% guard. No defaults change; the original b2 comparison, seven held-out workflows and broader native/TLS/fre qualification remain required.

| Workload | Baseline median | Candidate median | Native median | Paired wall change | Paired CPU change |
| --- | ---: | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.930s | 1.922s | 1.667s | +1.06% | +0.54% |
| token-phrase | 5.116s | 4.329s | 2.036s | -15.14% | -15.28% |

Three repeats of each of five source edits yield 15 paired observations per workflow. Independent verification passes 126 primary commands, 42 check commands and all 84 executed artifacts, with original assertions, wrong-edit failures and exact source restoration. Paired artifacts match; the existing cross-history layout variation remains recorded. Ratios are medians of paired ratios, so their direction need not match the ratio of separately computed medians. These are engineering gates on one shared host, not statistical significance claims.

Candidate `aa2f6ea` / `0e94d6d8` and baseline `9bd66cd` / `e965f566` use byte-identical exporter and wrapper binaries. The baseline VM is exactly tool78’s `60b00d7d`; candidate VM is `21d1e163`. Both enable resumable Calls, persistent registers and identical MIR/inlining settings, with four custom Cargo workers. Native/check controls use 18 workers, O0/incremental and default test concurrency. Strict checking remains enabled. Prebuilt std-MIR/tool setup is excluded and recorded by the workflow reports.

Token execution-stage medians are 3.751s baseline and 2.976s candidate; Cargo-stage medians are 1.282s and 1.268s. These separate medians describe where time was observed and are not additive or independent causal estimates. The exact whole-run profiles previously showed copies disappearing from interpreted operations, reducing native re-entries from about 22.4 million to 2.65 million. This supports the intended mechanism.

The candidate remains slower than this native control: token median 4.329s versus 2.036s, folded 1.922s versus 1.667s. This is a useful reduction in the custom runtime’s gap, not parity or large-codebase readiness. No LLVM/external guest backend was added.

[Exact gate ratios](gate-evaluation.json) · [Final verification](final-verification.json) · [Protocol and pre-measurement control correction](../../benchmarks/experiments/resumable-native-calls/COPY-TRANSITIONS-NEXT.md)
