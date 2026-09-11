# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a freshly built native control at the pinned source revision. Each test runs in a fresh process. Custom execution used the JIT with a 100,000,000,000-instruction limit and 150,000-live-allocation limit per body. Original sources and tests were preserved.

Collection tool: `81e0146dbd9d729d77040c50f9f50f71fbb2beb67a5ffc7c8a336d1baf328ff0`. Execution tool: `81e0146dbd9d729d77040c50f9f50f71fbb2beb67a5ffc7c8a336d1baf328ff0`. The original artifact pack and its collection provenance are verified independently of the selected VM.

| Outcome | Bodies |
|---|---:|
| passed | 16 |

Collected guest MIR flags: `-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Their recorded compilation invocation is hash-verified; native controls use their ordinary Cargo profile.

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
Passing a body with unavailable-call metadata means its tested path avoided those calls; it does not implement those platform functions.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 6.860 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
