# Aggregate projection controls pass

Eight new controls pass in debug and release, followed by all 13 legacy memory
proof controls and five scalar-IR controls in release. The four commands take
21.08 seconds including host compilation. Closure verifies 229 source bindings.
The first run's fixture integer-type compile failure is retained separately.

The reference handles every result width 0..64, ordered overlapping inputs,
zero padding, 468 large overlapping-copy cases, full-width branch conditions,
all tested short budgets, dead division/late faults, external-effect rejection,
shape/work limits, legacy behavior, local pointer bits and malformed return
annotations. Complete result bytes match an independent copy oracle; each
16-byte projection matches our ordinary bytecode interpreter's value, faults and
per-PC counts. All projections must follow the same original path.

The production entry points keep their existing limits and initialization
policy. Test-only proofs distinguish explicitly initialized bytes from a fresh
ordinary Call frame's zero bytes. Both still confine all memory accesses.
No aggregate projection is installed or executed as native guest code. Repeated
projection evaluation is a reference mechanism, not the intended runtime ABI.

Next census typed proof and projected native-expression eligibility on the exact
132 saved candidates. A future implementation must combine computation and use
one wider private result buffer, with complete Call-boundary qualification.
[Summary](summary.json), [closure](closure.json).
