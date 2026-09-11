# Identical-tool trajectory control: interrupted reverse run

The reverse experiment is incomplete. Its fourteen custom commands finished before the failed native command; their timings are descriptive only. No missing native sample is substituted and no forward/reverse average is treated as a candidate effect. Grouping did not eliminate identical-tool variation.

The complete forward run's median slot difference was +1141.4 ms. The completed custom phases of the interrupted reverse run had a median difference of -284.4 ms. Both slots used the same installed VM and exporter, with independent Cargo caches.

| Edit | Forward difference | Reverse custom-phase difference |
| --- | ---: | ---: |
| 1 | +728.2 ms | -93.8 ms |
| 2 | +1276.4 ms | -390.6 ms |
| 3 | +1383.7 ms | -459.5 ms |
| 4 | +962.9 ms | +3.5 ms |
| 5 | +1141.4 ms | -284.4 ms |

The native cold build returned 101 after rustc processes received SIGTERM. The source of those signals is unknown. Its elapsed time is retained only as failure evidence. The original driver assertions and its absent completion report are preserved. All fourteen custom artifacts match the complete forward run; original tests, runtime negative controls, pinned checkout, tool hashes, and source restoration were audited.

Decision: keep both optimization candidates isolated. Do not subtract these controls from candidate measurements. Runtime-heavy real-edit workloads are the next guide; small compile-time differences in this large Nu workflow remain unresolved.
