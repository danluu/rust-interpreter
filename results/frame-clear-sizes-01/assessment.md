# Saved frame-clear sample sizes

The census passed using two already closed adopted-runtime captures. It ran no
new guest commands and changed no generated code. All 409 block-test and 440
exhaustive-test Call/Return samples reconcile with the saved protocol census;
89 and 62 respectively fall in frame clearing. The closure verifies 32 inputs.

| Minimum payload bytes | Block samples | Exhaustive samples |
| --- | ---: | ---: |
| 256 | 63 | 50 |
| 512 | 35 | 41 |
| 1,024 | 18 | 21 |
| 2,048 | 4 | 5 |
| 4,096 | 4 | 0 |

Payload sizes come from the corresponding saved profile metadata, while sample
counts come exclusively from exact native self-PC attribution. Dynamic alignment
padding is unknown and is not assigned a size. A sample in the clearing loop
is not evidence that all its cost can be removed.

A mechanism restricted to large frames has a small measured scope. Do not
implement a hardware-specific bulk clear from nominal call-weighted bytes or
increase register-initialization proof limits: the separate closed register
census already found no current register zeroing for the observed direct calls.
Keep general frame-clearing improvements possible, but size native preparation
reuse across genuine source edits before committing to another small rewrite.
