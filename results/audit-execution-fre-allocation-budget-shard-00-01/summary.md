# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a freshly built native control at the pinned source revision. Each test runs in a fresh process. Custom execution used the JIT with a 100,000,000,000-instruction limit and 150,000-live-allocation limit per body. Original sources and tests were preserved.

Collection tool: `106eef0cd295590b613cf69bae62a3cc58e25dcadb307859bd90b7d047618766`. Execution tool: `96ebe61c955d79841e03ff55159996a1ae93f95bcb2b6b6bdcd0a60c9e9b8ca9`. The original artifact pack and its collection provenance are verified independently of the selected VM.

| Outcome | Bodies |
|---|---:|
| passed | 16 |

Collected guest MIR flags: `-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Their recorded compilation invocation is hash-verified; native controls use their ordinary Cargo profile.

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
Passing a body with unavailable-call metadata means its tested path avoided those calls; it does not implement those platform functions.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 6.668 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
