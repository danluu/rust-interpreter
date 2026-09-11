# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a freshly built native control at the pinned source revision. Custom execution used the JIT with a 100,000,000-instruction limit per body. Original sources and tests were preserved.

| Outcome | Bodies |
|---|---:|
| instruction-limited | 1 |
| passed | 57 |

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 7.034 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
