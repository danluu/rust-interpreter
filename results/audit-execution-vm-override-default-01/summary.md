# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a freshly built native control at the pinned source revision. Custom execution used the JIT with a 100,000,000-instruction limit per body. Original sources and tests were preserved.

Collection tool: `0d0d7b9092fe9e29320b35d7b04eed4655a81b7d21e0cd90bff9abaecf85ed34`. Execution tool: `0d0d7b9092fe9e29320b35d7b04eed4655a81b7d21e0cd90bff9abaecf85ed34`. The original artifact pack and its collection provenance are verified independently of the selected VM.

| Outcome | Bodies |
|---|---:|
| passed | 2 |

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 6.819 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
