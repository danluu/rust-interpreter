# Direct forwarding: thirteen production-edit workflows

The candidate wins **37/65** complete edited-command pairs against the prior custom JIT and **42/65** against native Rust. Original tests pass, every mode rejects the deliberately wrong edit, and all five source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-forward-anchored-tls](../paired-direct-forwarding-tls-01/summary.md) | 1.497 | 2.159 | 1.969 | -203.543 | -206.673 | 5/5 |
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-direct-forwarding-01/summary.md) | 1.817 | 3.514 | 3.480 | -50.601 | -68.515 | 5/5 |
| [fre-word64](../e2e-paired-fre-word64-direct-forwarding-01/summary.md) | 2.047 | 2.291 | 2.258 | -33.264 | -28.751 | 4/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-direct-forwarding-01/summary.md) | 1.683 | 1.717 | 1.695 | -20.436 | -15.499 | 4/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-direct-forwarding-01/summary.md) | 0.735 | 0.920 | 0.916 | -3.832 | -1.059 | 3/5 |
| [pgrust](../e2e-paired-pgrust-direct-forwarding-01/summary.md) | 0.637 | 0.514 | 0.515 | +5.942 | -2.441 | 1/5 |
| [fre-class-sequence](../e2e-paired-fre-class-sequence-direct-forwarding-01/summary.md) | 1.441 | 0.786 | 0.774 | -15.047 | -0.007 | 3/5 |
| [nushell](../e2e-paired-nushell-direct-forwarding-01/summary.md) | 0.675 | 0.448 | 0.438 | -6.721 | -0.038 | 4/5 |
| [ruff](../e2e-paired-ruff-direct-forwarding-01/summary.md) | 5.615 | 2.795 | 2.954 | +97.634 | -0.313 | 0/5 |
| [rg-aot](../e2e-paired-rg-aot-direct-forwarding-01/summary.md) | 0.573 | 0.200 | 0.202 | -7.029 | +0.066 | 3/5 |
| [nushell-type-relations](../e2e-paired-nushell-type-relations-direct-forwarding-01/summary.md) | 10.356 | 6.503 | 7.048 | +263.516 | +0.230 | 1/5 |
| [fre-grapheme-scalar-dfa](../e2e-paired-fre-grapheme-scalar-dfa-direct-forwarding-01/summary.md) | 1.462 | 0.853 | 0.874 | +2.815 | -0.129 | 2/5 |
| [fre-packed-literal-set](../e2e-paired-fre-packed-literal-set-direct-forwarding-01/summary.md) | 1.464 | 0.889 | 0.890 | +12.884 | -0.491 | 2/5 |

Negative changes mean faster commands. Each paired change is a median of the five per-edit differences; it need not equal a difference of separate medians. Cargo and execution stage medians need not add to the command median. All pairs, orders, cold commands, and setup costs remain in the individual reports. No outlier is discarded and no A/A median is subtracted. Five pairs per workflow on a shared host do not establish confidence intervals. Some workflows are different configurations of the same code, so aggregate win counts are descriptive rather than independent statistical samples.

The exporter recognizes functions containing only local addresses, one direct call forwarding complete arguments unchanged, and return. It resolves forwarding chains with cycle detection, then changes direct-call targets. All function IDs, argument and result addresses, frame layouts, static instruction counts, and serialized lengths stay fixed. A separate audit proves every one of the 91 original, invalid-edit, and valid-edit artifact pairs differs only in direct-call targets and exactly matches the transform applied to its baseline.

The first TLS-dependent workflow removes 10,468,047 interpreted calls per profiled execution, reducing calls from 40,540,305 to 30,072,258 without increasing generated native-code size. Both actual VM binaries produce identical complete profiles for each input artifact; these instrumented runs diagnose guest work rather than supply benchmark timings.

Commands include Cargo, strict type and borrow checking, bytecode export, launch, JIT construction, and existing test execution. Tool bootstrap, downloads, and reusable standard-library MIR setup are outside these timers and separately recorded. The JIT uses the project’s own AArch64 emitter. Native Rust is the control. These selected library workloads do not establish whole-application support.

All 125 bytecode tests, two 23,502-command native suites, and the auxiliary gates pass. Current TLS validation passes 245 commands. Fresh fre execution preserves all 389 prior classifications: 320 pass, 62 are blocked in lowering, and 7 are ignored. Actual unwinding, guest threads, and arbitrary platform calls remain unsupported. The TLS workflow explicitly enables normal-return try callbacks; caught-panic behavior is not synthesized.

Two reporting interruptions were repaired from retained evidence: private test names were read from the private raw records, and an auxiliary auditor was recovered byte-for-byte from its archive after the mutable build directory disappeared. The measured sources and both immutable tool builds were unchanged. No timed command was repeated for these repairs.

[Current correctness gates](../direct-forwarding-default-validation-01.json), [fresh fre coverage](../audit-execution-fre-direct-forwarding-01/summary.md), [first paired TLS workload](../paired-direct-forwarding-tls-01/summary.md).
