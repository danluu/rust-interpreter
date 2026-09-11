# Resumable folded exact-code profile

Three fresh executions of the original artifact pass every assertion using
`e1bec3e` / tool `035ef708`, VM `07020e6e`. Only resumable Calls and persistent
registers are enabled. The profiler verifies each owned PID, parent, start time,
command, cwd, executable mapping, VM/artifact hashes and frozen sources.
The code dump comes from that same process after successful execution.

The 2,315 thread self samples partition exactly; all 2,307
generated samples resolve inside the published code and its entry ranges.
All three windows have zero unresolved generated PCs. No instruction-profile
instrumentation was enabled. These are partial, perturbed windows, not latency
measurements, whole-run cost estimates or speedup predictions.

| Observed category | Samples | Share of thread samples |
| --- | ---: | ---: |
| generated_code | 2,307 | 99.65% |
| native_boundary_self | 5 | 0.22% |
| heap_inclusive | 3 | 0.13% |

Generated samples can also be partitioned by exact emitted instructions:

| Instruction class | Samples | Share of thread samples |
| --- | ---: | ---: |
| native_zero_range | 1,303 | 56.29% |
| other_generated | 732 | 31.62% |
| cursor_load_store | 129 | 5.57% |
| direct_register_array_load | 35 | 1.51% |
| direct_register_array_store | 92 | 3.97% |
| frame_descriptor_load_store | 16 | 0.69% |

Entry ranges contain 1,538 Call, 92 Return and
677 ordinary-region samples, including their wrappers/failure tails.
Range classification is not itself an opcode cost model. Frame-descriptor
loads/stores use x20 only under this mode's ABI; large computed accesses remain
unclassified. Each exact zeroing sequence includes loop control as well as stores.

Logical instruction totals: 4,138,403,285, 4,138,403,285, 4,138,403,285.
Published code is 5,824,108 bytes in every window; no functions decline.

The new E2E result passed folded's 10% gate but missed token's 20% gate.
The substantial exact clearing share now justifies one bounded bulk-clearing
experiment while preserving every initialized byte. This revisits clearing
because the execution architecture and evidence changed; parked frame-layout/
zero-elision proposals remain parked. Keep the original complete-command gates.

[Disjoint samples](summary.json) · [Exact code attribution](generated-attribution.json) ·
[E2E result](../resumable-e2e-01/assessment.md) ·
[Selected experiment](../../benchmarks/experiments/resumable-native-calls/BULK-CLEAR-NEXT.md)
