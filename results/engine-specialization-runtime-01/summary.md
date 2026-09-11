# Separate interpreter and JIT loops: runtime comparison

The engine is selected once at entry, then the VM uses a compile-time loop specialization. Assertion emission remains enabled. The rejected cold fault-formatting helper is absent. All 58 bytecode tests, 23,277 native differential/rejection commands, and 93 launcher checks pass. All nine production-edit workflows also pass, with wrong-edit rejection in every mode and restored source pins. The change is retained.

| Workload / engine | Qualified control | Separate loops | Candidate pair wins |
|---|---:|---:|---:|
| word64-default / Interpreter | 16.250 s | 15.336 s | 3/3 |
| sha1-inline8 / Interpreter | 5.271 s | 4.858 s | 3/3 |
| word64-default / JIT | 2.331 s | 2.301 s | 5/5 |
| word64-inline8 / JIT | 1.581 s | 1.554 s | 5/5 |
| sha1-inline8 / JIT | 0.706 s | 0.662 s | 5/5 |

Every comparison uses identical saved production-workflow bytecode for the two VMs, with alternating order. The candidate wins all three interpreter pairs in both workloads and all five JIT pairs in each configuration. Instruction counts and peak guest memory remain identical. The VM binary grows by 18,208 bytes to 731,280 bytes. Instrumented profiles are separate from performance samples.

Interpretation improves about 6% for word64 and 8% for SHA-1 relative to the last qualified VM. JIT improvements are smaller: about 1% for default word64, 2% at eightfold MIR thresholds, and 6% for SHA-1. Complete edit/test qualification passed. Native remains faster on the compute-heavy word64 and SHA-1 workflows; historical corpus differences also reflect compiler and host variation.

[Qualified production corpus and stage medians](../e2e-engine-specialization-corpus-01/summary.md).

[Validation and raw records](../engine-specialization-validation-01.json), [initial assertion regression](../jit-assertions-validation-01.json), [rejected cold formatter](../jit-cold-failure-comparison-01/summary.md).
