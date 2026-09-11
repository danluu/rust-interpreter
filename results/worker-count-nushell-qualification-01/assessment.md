# Nushell worker-count qualification

All nine primary commands and three independent checks satisfy their expected
outcomes, including the original fourteen tests and wrong-edit rejections. All
six corresponding artifacts match. Eleven frozen inputs, six heavy-wrapper
traces, both tool78 binaries and exact source restoration verify. The engines
use identical ordinary JIT/leaf-inlining/std-MIR settings; only custom Cargo
workers differ, four versus eighteen. Native/check retain eighteen workers,
O0/incremental and default test concurrency.

| Cold mode | Wall seconds | Child CPU seconds |
| --- | ---: | ---: |
| native | 39.589 | 264.164 |
| baseline | 61.125 | 178.047 |
| candidate | 30.550 | 233.596 |

Candidate/baseline cold ratios are 0.4998010467 wall and 1.3119883805 CPU.
This is a substantial latency/CPU tradeoff in one qualification, excluded from
adoption measurements. The predefined repeated study and its CPU guard remain
required. CPU time is not an instruction count, energy measure or CPU-utilization
trace. No worker-count change is retained from this pilot alone.

Median edited wall seconds: native 11.003971, baseline 4.971574,
candidate 4.956564. Tool installation, downloads and prebuilt std-MIR
setup are excluded from the cold command times; OS caches were not cleared.

[Workflow checks](verification.json), [configuration and full-precision results](configuration-verification.json),
[all measurements](summary.json).
