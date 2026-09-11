Three fresh original-artifact executions pass with tool `0e94d6d8`, source `aa2f6ea`,
resumable calls and persistent registers. All assertions pass, no JIT function
declines, and each sampled process has matching identity, mapping and code dump.
All 2,297 thread self samples partition exactly; all 2,289 generated
samples map to their own process’s emitted code, with zero unresolved samples.

| Sample category | Count | Share |
| --- | ---: | ---: |
| generated_code | 2,289 | 99.65% |
| native_boundary_self | 5 | 0.22% |
| other_host_self | 1 | 0.04% |
| heap_inclusive | 1 | 0.04% |
| dispatcher_self | 1 | 0.04% |

| Exact instruction class | Count | Share of thread samples |
| --- | ---: | ---: |
| native_zero_bulk | 855 | 37.22% |
| other_generated | 1,011 | 44.01% |
| native_zero_range | 87 | 3.79% |
| direct_register_array_store | 135 | 5.88% |
| cursor_load_store | 161 | 7.01% |
| frame_descriptor_load_store | 18 | 0.78% |
| direct_register_array_load | 22 | 0.96% |

Exact bulk and tail clearing together account for 41.01% of sampled thread time.
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
