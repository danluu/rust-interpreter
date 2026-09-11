# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a freshly built native control at the pinned source revision. Custom execution used the JIT with a 100,000,000,000-instruction limit per body. Original sources and tests were preserved.

Collection tool: `76af5541c56a2cd58ad9eae75b91ee9f3c6ad4327f0a8d082cde19573a2d6404`. Execution tool: `76af5541c56a2cd58ad9eae75b91ee9f3c6ad4327f0a8d082cde19573a2d6404`. The original artifact pack and its collection provenance are verified independently of the selected VM.

| Outcome | Bodies |
|---|---:|
| ignored | 7 |
| lowering-blocked | 62 |
| passed | 303 |
| runtime-unsupported-call | 17 |

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
Passing a body with unavailable-call metadata means its tested path avoided those calls; it does not implement those platform functions.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 6.705 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
