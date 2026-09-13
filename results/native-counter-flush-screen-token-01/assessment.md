# Native register counters plus successor-live spills: parked

All40 changed-source commands satisfy the original assertions, deliberately wrong
edit, native outcomes, identical bytecode/catalogs and source restoration. The
predeclared performance gate fails: paired wall ratio0.9988592008 (−0.114%), CPU
0.9998213209 (−0.018%), against A/A envelopes2.2543% wall and2.0291% CPU. The wall
margin is1.0214021732. These results do not resolve a small effect. Do not retime
this unchanged candidate or start the full comparison or held-out controls.
The short-screen native ratio1.6861 is not an adopted or general codebase ratio.

Toolab753e4c / VM8ce8dcc3 passes532 workspace tests in each build profile,
119 strict/cache controls, three exact entropy-bound original profiles and12
harness tests. Calls/returns, per-PC logical counts, entries, memory and entropy
match the adopted35df4077 tool exactly; no new function declines occur. Both
saved unprofiled captures reconstruct exactly, all1101/1305 functions. Counter
entry/exit changes add637,040/742,564 bytes; successor spills remove197,384/238,016,
leaving net growth439,656/504,548 bytes. All per-scope word counts are accounted.
The profiled captures fit16 MiB at12,122,864/14,663,652/2,044,588 bytes.

Keep the runtime patch on experiment/native-counter-flush-20260913. Main retains
the adopted memory-backed counters and original spill rule. The first build
admission performed no work; the next build exposed three historical observer
configuration failures (274 other library tests passed). Their explicit original-
spill switch fixed the fixtures; production code did not change. The successful
build's admitted setup cost was111.63s, including both test profiles and tool
installation; the final0.186s executable-build command alone is not setup cost.

Next: inspect actual adjacent load/store instructions in the saved, partitioned
memory-data spans, with sample attribution and emitted-word limits. Establish
coverage before any paired-access prototype. Preserve the old selector, budget,
ABI-copy and counter negative results; do not assume the whole memory-data
sample bucket is eligible or that instruction-count savings imply elapsed gain.
