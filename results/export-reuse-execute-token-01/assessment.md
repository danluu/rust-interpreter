# Actual persistent function reuse

Both complete eight-state production histories pass with original test
assertions and exact retained bytecode. Token edits skip 5,178–5,202 of 5,375
functions; folded edits skip 976–1,040 of 1,045. Wrong edits fail in the guest,
and source restoration rebuilds and matches the corresponding retained state.
The reuse mode executes no second lowering graph or function-cost observer.

Qualification also passes 50 exporter tests in debug/release, 337 complex
fixture commands, 293 semantic-edit commands and 98 cache fault/publication
commands. The source is `b81cd1f`; VM and wrapper binaries remain the original
control. Reuse is explicit (`RUST_INTERP_FUNCTION_CACHE=reuse`) and disabled by
default. Strict rustc type and borrow checking remains mandatory. Corrupt or
missing files regenerate; red or unsupported functions fully lower. A failed
publication never becomes a successful incremental predecessor.

This is a correctness and cost-attribution result, not a speedup claim. Median
edited token intervals are 145.03 ms file load (including namespace/read/decode),
139.49 ms file encoding, 7.53 ms writing, 36.16 ms function decoding, 131.19 ms
binding and 19.85 ms compiler green checks. These costs consume the previously
measured ~444 ms function-lowering opportunity. Folded's corresponding costs
are 39.67, 34.29, 2.38, 8.42, 14.33 and 16.70 ms. No paired performance primary
was run on this representation.

Next address measured representation costs: the pinned SHA-256 crate selects
its software ARM backend unless the optional assembly feature is enabled, and
plain Vec<u8> serialization visits bytes individually. Keep checksum and wire
semantics, validate bulk serialization against the legacy bytes, and measure
again before a predeclared edited end-to-end screen. Cached binding remains a
separate cost; global optimization, graph construction and strict frontend
checking still execute.

See `summary.json` and `../export-reuse-execute-folded-01/summary.json` for exact
tools, commands, source hashes, staged-file bounds and per-state counts.
