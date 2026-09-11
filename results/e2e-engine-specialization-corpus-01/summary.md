# Separate interpreter/JIT loops: production-edit qualification

Assertion emission initially improved JIT runtime but slowed interpretation. Choosing the engine once at entry and specializing the loop restores interpretation performance while retaining assertion emission. A separate cold fault-formatting experiment was rejected and is absent from this build. All nine workflows pass on one frozen build with five production refactors, unchanged original tests, wrong-edit rejection in every mode, and restored source pins.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-engine-specialization-01/summary.md) | 1.885 s | 15.814 s | 3.203 s |
| [pgrust](../e2e-workflow-pgrust-engine-specialization-01/summary.md) | 0.691 s | 0.773 s | 0.551 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-engine-specialization-01/summary.md) | 1.410 s | 0.805 s | 0.794 s |
| [nushell](../e2e-workflow-nushell-engine-specialization-01/summary.md) | 0.674 s | 0.454 s | 0.441 s |
| [ruff](../e2e-workflow-ruff-engine-specialization-01/summary.md) | 5.761 s | 3.023 s | 3.026 s |
| [rg-aot](../e2e-workflow-rg-aot-engine-specialization-01/summary.md) | 0.543 s | 0.204 s | 0.208 s |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-engine-specialization-01/summary.md) | 15.319 s | 7.331 s | 7.551 s |
| [fre-word64-inline8](../e2e-workflow-fre-word64-inline8-engine-specialization-01/summary.md) | 2.410 s | 13.533 s | 2.642 s |
| [pgrust-sha1-inline8](../e2e-workflow-pgrust-sha1-inline8-engine-specialization-01/summary.md) | 0.763 s | 5.393 s | 1.178 s |

Complete commands include Cargo, strict checking, export, launch, and execution. These remain selected existing tests in larger workspaces, not full applications or suites. Explicit MIR inlining retains development checks. Cold commands and stage medians are retained in the JSON; metadata-sysroot commands exclude the separately recorded 10.997 s reusable setup.

| Identical bytecode / engine | Qualified control | Candidate | Pair wins |
|---|---:|---:|---:|
| word64-default / Interpreter | 16.250 s | 15.336 s | 3/3 |
| sha1-inline8 / Interpreter | 5.271 s | 4.858 s | 3/3 |
| word64-default / JIT | 2.331 s | 2.301 s | 5/5 |
| word64-inline8 / JIT | 1.581 s | 1.554 s | 5/5 |
| sha1-inline8 / JIT | 0.706 s | 0.662 s | 5/5 |

Every runtime comparison uses the same bytecode for old and new VMs. All instruction counts and peak guest memory match. All 58 bytecode tests, 23,277 native differential/rejection commands, and 93 launcher checks pass. The VM binary grows by 18,208 bytes relative to the qualified control. Historical command differences also reflect compiler and host variation; use the controlled runtime comparisons to assess the VM change.

[Validation and raw records](../engine-specialization-validation-01.json), [initial assertion regression](../jit-assertions-validation-01.json), [rejected cold formatter](../jit-cold-failure-comparison-01/summary.md).
