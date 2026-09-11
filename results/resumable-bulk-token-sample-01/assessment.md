Fresh executions of the original artifact pass all assertions using tool `78e60cdd` (source `001065a`), VM `60b00d7d`, with resumable Calls and persistent registers enabled. Each of three owned processes has a matching code dump, verified PID, parent, command, cwd, artifact and VM hashes. No instruction-profile instrumentation was enabled.

All 7,644 thread self samples partition exactly; all 5,569 generated samples resolve inside the same process’s published code. These are partial, perturbed windows, not latency measurements or speedup predictions.

| Sample category | Count | Share |
| --- | ---: | ---: |
| native_boundary_self | 1,192 | 15.59% |
| other_host_self | 132 | 1.73% |
| generated_code | 5,569 | 72.85% |
| heap_inclusive | 372 | 4.87% |
| dispatcher_self | 156 | 2.04% |
| memory_copy_inclusive | 163 | 2.13% |
| jit_preparation_inclusive | 49 | 0.64% |
| frame_reservation_inclusive | 11 | 0.14% |

| Exact instruction class | Count | Share of thread samples |
| --- | ---: | ---: |
| native_zero_range | 447 | 5.85% |
| native_abi_byte_copy | 264 | 3.45% |
| native_zero_bulk | 283 | 3.70% |
| direct_register_array_store | 537 | 7.03% |
| cursor_load_store | 865 | 11.32% |
| other_generated | 2,992 | 39.14% |
| frame_descriptor_load_store | 77 | 1.01% |
| direct_register_array_load | 104 | 1.36% |

The analyzer now recognizes the complete 64-byte bulk-loop prefix only when followed by its exact existing tail. The prefix and tail remain disjoint categories. Six earlier three-window reports reproduce unchanged, with 660 altered/truncated-sequence rejections, 72 false-option checks and four incompatible-range checks. No runtime code changed.

The remaining native-boundary share is 15.59%; exact bulk and small-loop clearing together account for 9.55%. Boundary self PCs include run_resumable and Boundary new/finish/validate_extents. Whole-execution counters record about 22.4 million native entries versus 110.5 million native Calls; determine the remaining interpreted operations before designing a helper-call boundary. Direct register-array loads/stores account for 8.39%, so register allocation alone is not clearly the first choice.

[Disjoint samples](summary.json) · [Exact emitted-code attribution](generated-attribution.json) · [Analyzer qualification](../resumable-bulk-profile-tools-01/summary.json) · [Existing E2E decision](../resumable-bulk-replication-01/assessment.md)
