# Full fre coverage with MIR3 and larger inlining

All **389 original test bodies lower**. Execution retains **320 passing tests**;
**62 stop at the JIT’s 16 MiB native-code limit**, and **7 remain ignored**.
Every previous passing test still passes. The 62 code-limited tests previously hit
the exporter’s function-expansion limit. Their native controls pass, but their
JIT guest bodies do not execute. This moves the blocker; it adds no JIT passes yet.

The original whole collection reached the unchanged 1 GiB artifact-pack bound.
The completed survey uses 25 batches of at most 16 bodies, preserving both the
64 MiB per-body and 1 GiB per-pack bounds. Each retained program and its exact
metadata sidecar is verified by recorded hashes. One fresh native build at the
pinned revision serves every batch; its binary, toolchain, test listing, and source
pin are verified, and each test runs in a fresh native and guest process.
All 382 ordinary native tests pass. Original sources and tests are unchanged.

Four negative checks reject altered native hashes, source pins, test listings,
and guest MIR flags before any test body runs. Compiler metadata/object caches
were reclaimed only after their batches completed, retaining programs, sidecars,
executables, libraries, native controls, and reports.

The flags are `-Zmir-opt-level=3 -Zinline-mir-threshold=400
-Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`, with bounded
bytecode leaf inlining and the explicit normal-return try-callback option. Rust
type and borrow checking remain strict; actual unwinding remains unsupported.
The collector’s exact invocation and RUSTFLAGS are recorded and hashed.

The survey originally recorded these 62 outcomes as generic `jit-failure`.
This report classifies them as `jit-code-limited` only after checking every exact
VM diagnostic. Raw outcomes are preserved. This is coverage evidence, not a
production-edit benchmark or whole-application support claim.

The own-interpreter replay is complete: **50 of the 62 code-limited programs pass**,
11 reach the smaller 1-billion-instruction diagnostic budget, and one reaches the
100,000-live-allocation cap. An isolated logging build confirms that last refusal
at 100,000 live allocations, 4,673,944 heap bytes, and a 10-byte request; increasing
the byte budget alone from 64 to 256 MiB does not resolve it. The original test
builds 117,649 vectors before deduplicating them. No defaults or tests were changed.
Across the two own engines, 370 ordinary bodies now have passing execution evidence;
this is still 320 JIT passes. The next experiment generates native functions when
execution first needs them, retaining the code cap and strict frontend checks.

[Same-JIT MIR timing comparisons](../direct-forwarding-mir-tuning-01/summary.md),
[forwarding production-edit corpus](../paired-direct-forwarding-corpus-01/summary.md).
