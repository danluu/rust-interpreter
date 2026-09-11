# Resumable token exact-code profile

Three fresh executions of the original artifact pass every assertion using
`e1bec3e` / tool `035ef708`, VM `07020e6e`. Only resumable Calls and persistent
registers are enabled. The profiler verifies each owned PID, parent, start time,
command, cwd, executable mapping, VM/artifact hashes and frozen sources.
The code dump comes from that same process after successful execution.

The 6,964 thread self samples partition exactly; all 5,295
generated samples resolve inside the published code and its entry ranges.
All three windows have zero unresolved generated PCs. No instruction-profile
instrumentation was enabled. These are partial, perturbed windows, not latency
measurements, whole-run cost estimates or speedup predictions.

| Observed category | Samples | Share of thread samples |
| --- | ---: | ---: |
| native_boundary_self | 939 | 13.48% |
| other_host_self | 92 | 1.32% |
| generated_code | 5,295 | 76.03% |
| heap_inclusive | 317 | 4.55% |
| dispatcher_self | 134 | 1.92% |
| memory_copy_inclusive | 127 | 1.82% |
| jit_preparation_inclusive | 47 | 0.67% |
| frame_reservation_inclusive | 13 | 0.19% |

Generated samples can also be partitioned by exact emitted instructions:

| Instruction class | Samples | Share of thread samples |
| --- | ---: | ---: |
| native_zero_range | 1,214 | 17.43% |
| native_abi_byte_copy | 212 | 3.04% |
| direct_register_array_store | 436 | 6.26% |
| cursor_load_store | 842 | 12.09% |
| other_generated | 2,431 | 34.91% |
| frame_descriptor_load_store | 76 | 1.09% |
| direct_register_array_load | 84 | 1.21% |

Entry ranges contain 2,193 Call, 503 Return and
2,599 ordinary-region samples, including their wrappers/failure tails.
Range classification is not itself an opcode cost model. Frame-descriptor
loads/stores use x20 only under this mode's ABI; large computed accesses remain
unclassified. Each exact zeroing sequence includes loop control as well as stores.

Logical instruction totals: 13,369,438,381, 13,369,460,558, 13,369,557,219.
Published code is 14,608,884 bytes in every window; no functions decline.
The original workload uses randomness; differing counts are preserved.
The native-boundary category includes run_resumable and Boundary new/finish/
validate_extents self PCs. It remains a separate optimization candidate.

The new E2E result passed folded's 10% gate but missed token's 20% gate.
The substantial exact clearing share now justifies one bounded bulk-clearing
experiment while preserving every initialized byte. This revisits clearing
because the execution architecture and evidence changed; parked frame-layout/
zero-elision proposals remain parked. Keep the original complete-command gates.

[Disjoint samples](summary.json) · [Exact code attribution](generated-attribution.json) ·
[E2E result](../resumable-e2e-01/assessment.md) ·
[Selected experiment](../../benchmarks/experiments/resumable-native-calls/BULK-CLEAR-NEXT.md)
