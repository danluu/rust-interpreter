# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a freshly built native control at the pinned source revision. Each test runs in a fresh process. Custom execution used the JIT with a 100,000,000,000-instruction limit per body. Original sources and tests were preserved.

Collection tool: `366567663f043d4a2370d72ae7eeade60bb91cda07ac19e12831491b4f606504`. Execution tool: `366567663f043d4a2370d72ae7eeade60bb91cda07ac19e12831491b4f606504`. The original artifact pack and its collection provenance are verified independently of the selected VM.

| Outcome | Bodies |
|---|---:|
| passed | 16 |

Explicit VM options: `--jit-persistent-registers --jit-resumable-calls --allocation-limit 150000`. Per-body runtime counters are retained in the raw results.

Collected guest MIR flags: `-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Their recorded compilation invocation is hash-verified; native controls use their ordinary Cargo profile.

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
Passing a body with unavailable-call metadata means its tested path avoided those calls; it does not implement those platform functions.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 6.519 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
