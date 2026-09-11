# Execution coverage: fre / fre-kernels

Compared retained ordinary test bodies with a hash-verified native control reused from the preceding batch at the pinned source revision. Each test runs in a fresh process. Custom execution used the JIT with a 100,000,000,000-instruction limit per body. Original sources and tests were preserved.

Collection tool: `9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223`. Execution tool: `9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223`. The original artifact pack and its collection provenance are verified independently of the selected VM.

| Outcome | Bodies |
|---|---:|
| ignored | 1 |
| passed | 15 |

Explicit VM options: `--jit-persistent-registers --jit-resumable-calls --allocation-limit 150000`. Per-body runtime counters are retained in the raw results.

Collected guest MIR flags: `-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Their recorded compilation invocation is hash-verified; native controls use their ordinary Cargo profile.

Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.
A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.
Passing a body with unavailable-call metadata means its tested path avoided those calls; it does not implement those platform functions.
This is a coverage survey, not a complete suite or a production-edit speedup comparison.

Native build: 0.000 s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements.
