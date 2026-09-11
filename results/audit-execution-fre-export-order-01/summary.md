# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a freshly built native control at the pinned source revision. Custom execution used the JIT with a 100,000,000,000-instruction limit per body. Original sources and tests were preserved.

Collection tool: `67a3a330361963416e615816c84c0f80cf2dae3d865e5d41a9e5e97e285ac71e`. Execution tool: `67a3a330361963416e615816c84c0f80cf2dae3d865e5d41a9e5e97e285ac71e`. The original artifact pack and its collection provenance are verified independently of the selected VM.

| Outcome | Bodies |
|---|---:|
| lowering-blocked | 158 |
| passed | 231 |

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 6.402 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
