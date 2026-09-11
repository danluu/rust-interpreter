Fresh executions of the original artifact pass all assertions using tool `78e60cdd` (source `001065a`), VM `60b00d7d`, with resumable Calls and persistent registers enabled. Each of three owned processes has a matching code dump, verified PID, parent, command, cwd, artifact and VM hashes. No instruction-profile instrumentation was enabled.

All 2,548 thread self samples partition exactly; all 2,538 generated samples resolve inside the same process’s published code. These are partial, perturbed windows, not latency measurements or speedup predictions.

| Sample category | Count | Share |
| --- | ---: | ---: |
| generated_code | 2,538 | 99.61% |
| other_host_self | 1 | 0.04% |
| native_boundary_self | 5 | 0.20% |
| heap_inclusive | 3 | 0.12% |
| dispatcher_self | 1 | 0.04% |

| Exact instruction class | Count | Share of thread samples |
| --- | ---: | ---: |
| native_zero_bulk | 918 | 36.03% |
| native_zero_range | 103 | 4.04% |
| frame_descriptor_load_store | 27 | 1.06% |
| other_generated | 1,114 | 43.72% |
| direct_register_array_store | 125 | 4.91% |
| cursor_load_store | 219 | 8.59% |
| direct_register_array_load | 32 | 1.26% |

The analyzer now recognizes the complete 64-byte bulk-loop prefix only when followed by its exact existing tail. The prefix and tail remain disjoint categories. Six earlier three-window reports reproduce unchanged, with 660 altered/truncated-sequence rejections, 72 false-option checks and four incompatible-range checks. No runtime code changed.

Exact bulk and small-loop clearing together account for 40.07%. Native boundaries account for only 0.20%; improving those boundaries is unlikely to address this workload’s dominant sampled cost. Private-array reuse and argument-only clearing remain parked by their prior low-scope censuses; a broader frame-layout proof would be a separate experiment.

[Disjoint samples](summary.json) · [Exact emitted-code attribution](generated-attribution.json) · [Analyzer qualification](../resumable-bulk-profile-tools-01/summary.json) · [Existing E2E decision](../resumable-bulk-replication-01/assessment.md)
