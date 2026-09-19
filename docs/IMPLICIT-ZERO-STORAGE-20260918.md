# Implicit-zero register storage: closed primary result

The custom resumable JIT prototype passed correctness qualification, but its
changed-source primary did not establish a reliable latency improvement. Main
retains the adopted scratch/scalar runtime. Larger comparisons were cancelled.

A bounded whole-function proof identifies registers whose logical upper64bits
are always zero. Reused backing can still contain wide values, because the VM
already elides initialization when every read follows a write. The prototype
therefore reconstructs native high reads and persistent reloads, omits proven
high stores, and repairs classified operands before interpreting them. Code and
proof publication are coupled; retained proof entries are capped at8MiB.
Strict type/borrow checking and all initialization, fault and budget rules remain.

The saved-code census covers126/1,933 and119/1,429 generated self samples in two
original token tests. Its conservative repair counts are6.54M/8.51M operands.
These observations justified a prototype, not a speed claim. Native code in
three original profiles shrinks about2–3% while every logical PC, memory peak,
entropy count and scalar execution count matches the adopted controls.

Nine focused controls per profile cover physically poisoned backing, large
register offsets, persistent reloads, C ABI preservation, metadata/code bounds,
reconstruction after admission exhaustion, aliases, wide/narrow frame reuse,
TLS callbacks, indirect-handle rejection, faults and every budget prefix.
All628 Rust tests/profile and427 Python tests pass (15ignored Rust observers,
22Python skips). All121strict/cache commands pass, including unreachable
borrow/type rejection and an actual partially checked artifact rejection.

The40-command fre history retains original, wrong, five valid edited and restored
sources. The median paired wall ratio is0.978171695, an observed2.18% improvement,
inside4.36% A/A variation. The wall margin1.021751132 fails the original threshold.
CPU ratio0.986097055 and margin1.026384095 pass. All assertions and restoration
pass; the paired candidate/native wall ratio is1.662316689. This failed gate
establishes no reliable gain and is not proof of zero benefit.

The isolated tool3e53b127 uses VM8e369c0f and unchanged exporter cf4b3499 /
wrapper45bca4f2. The adopted control remains df4006e0 /VM6ac4dd9e.
Experimental source and full evidence are retained on
`experiment/narrow-register-storage-20260918`, including
`results/implicit-zero-storage-screen-token-01`. The closure verifies1,674files
and56artifacts. No unchanged rerun or larger history will follow this result.

The next diagnostic will separate full-width interpreter reads from operations
that already mask or truncate their operands. Removing unnecessary repairs
could change the cost balance, but requires a typed semantic census and a new
qualified candidate. Compiler/Cargo work remains in its separate workstream.
The engine still supports selected functions/test bodies, not arbitrary Rust
applications with complete thread, unwind and operating-system semantics.
