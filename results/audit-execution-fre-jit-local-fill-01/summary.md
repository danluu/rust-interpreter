# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a freshly built native control at the pinned source revision. Custom execution used the JIT with a 100,000,000,000-instruction limit per body. Original sources and tests were preserved.

Collection tool: `4227fc2287d5cf25e18327d9c7261bb95feb0f41e038bec050f15f1abcc8ffb6`. Execution tool: `2df1456c872e31670fca3c001d6a307d8a23754a591747bbbaca365d8a098322`. The original artifact pack and its collection provenance are verified independently of the selected VM.

| Outcome | Bodies |
|---|---:|
| lowering-blocked | 158 |
| passed | 231 |

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 6.910 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
