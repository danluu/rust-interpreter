Three fresh original-artifact executions pass with tool `0e94d6d8`, source `aa2f6ea`,
resumable calls and persistent registers. All assertions pass, no JIT function
declines, and each sampled process has matching identity, mapping and code dump.
All 7,186 thread self samples partition exactly; all 6,459 generated
samples map to their own process’s emitted code, with zero unresolved samples.

| Sample category | Count | Share |
| --- | ---: | ---: |
| generated_code | 6,459 | 89.88% |
| native_boundary_self | 160 | 2.23% |
| other_host_self | 39 | 0.54% |
| heap_inclusive | 410 | 5.71% |
| jit_preparation_inclusive | 53 | 0.74% |
| dispatcher_self | 38 | 0.53% |
| memory_copy_inclusive | 15 | 0.21% |
| frame_reservation_inclusive | 12 | 0.17% |

| Exact instruction class | Count | Share of thread samples |
| --- | ---: | ---: |
| native_zero_range | 540 | 7.51% |
| native_abi_byte_copy | 303 | 4.22% |
| native_zero_bulk | 339 | 4.72% |
| direct_register_array_store | 617 | 8.59% |
| other_generated | 3,545 | 49.33% |
| cursor_load_store | 907 | 12.62% |
| direct_register_array_load | 104 | 1.45% |
| frame_descriptor_load_store | 104 | 1.45% |

Exact bulk and tail clearing together account for 12.23% of sampled thread time.
The existing qualified analyzer is unchanged. New native transfer loops remain
in `other_generated`; its old ABI byte-copy pattern uses different registers
and does not classify the new transfer tails as ABI copies. No narrower cost
claim is made for grouped instructions.

These are partial, perturbed windows, not latency measurements or predicted
speedups. The source bytecode hashes match the older tool78 profile artifacts.
The current token boundary share is 2.23% versus 15.59% in that earlier capture;
the completed edit/build/test benchmarks separately measure the runtime gain.

[Thread samples](summary.json) · [Exact code attribution](generated-attribution.json) ·
[Protocol](../../benchmarks/experiments/resumable-native-calls/POST-COPY-PROFILES.md)

The first analysis wrapper supplied a relative script filename, which failed
the analyzer’s existing absolute-path evidence check before publishing a
report. Only analysis was rerun, with absolute filenames. The three captured
executions, analyzer sources and their results were not modified.

Full guest instruction totals vary slightly across the three processes
(13,369,468,707 to 13,369,519,784); native entries range from 2,648,087 to
2,648,161. These are preserved per-process observations, not identical-work
latency replicates. The separate controlled E2E histories determine speed.
