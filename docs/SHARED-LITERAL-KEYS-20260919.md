# Share function-key hashing within a checked request

The parent literal candidate reduced miss compilation in the parser diagnostic,
but its changed-source primary failed the wall gate: ratio 0.969685 plus 0.032002
control variation. It remains unadopted. Key construction is now a larger measured
preparation cost than miss emission: medians 10.278 ms and 7.103 ms per worker.
[Parent evidence](PARAMETERIZED-LITERALS-20260919.md).

The new experimental feature shares only the normalized Function digest and its
serialized length. Each fully validated, immutable Program owns private OnceLock
cells, initialized lazily for functions actually needed by either worker. Current
callee layout, initialization requirements, scalar proofs, numeric function ID,
emitter identity and runtime context remain inputs to each worker's complete key.
The cells contain no native code, guest state, borrowed addresses or previous
Program references. A different request constructs a different owner and cache.

Declared retained cache storage is bounded to 4 MiB and 65,536 functions. Cache
allocation refusal or too many functions falls back to uncached hashing. A body
that exceeds the existing 4 MiB key bound remains inadmissible; failed computations
are memoized too. The complete key charges the entire normalized body preimage
plus current outer inputs, not merely the short digest. Added domain/framing
bytes make this bound conservative relative to the previous inline format.
The new literal-v2 domain separates the composed identity from literal-v1.

Focused qualification passes 36 template and 3 policy controls per profile,
plus 31 parameterization-only template controls. New checks cover two concurrent
readers with exactly one computation, cached/uncached equality at the logical
size boundary, mismatched Program ownership, current callee/options changes,
storage bounds and oversized-body rejection.
[Focused proof](../results/shared-literal-keys-focused-01/summary.json).

Full workspace qualification passes 678 Rust tests per profile (17 ignored),
33 diagnostic integrations, 10 feature-off session checks, 31 feature-off template
checks and the default VM build. The unchanged 442 Python controls (22 skips) are
reused through exact hashes. All 48 owned servers and 92 clients have terminal
records. [Workspace proof](../results/shared-literal-keys-qualification-01/summary.json). Actual parser replay must verify
every cache hit against fresh native emission; phase attribution then decides
whether a new end-to-end primary is justified. Sharing may introduce contention
or setup overhead. No performance gain or default-runtime adoption is established.
