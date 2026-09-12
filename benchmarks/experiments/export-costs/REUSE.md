# Measure function reuse before choosing a cache boundary

Fixed frame clearing is parked after its combined es8 confirmation missed the
8% complete-command gate. The next opportunity is token export: graph lowering
costs 691ms, including 464ms in reachable MIR/local passes, 97ms in aggregate
finalization, 61ms in call optimization and 54ms in CFG optimization. These
inner intervals are nested; do not add them to the outer 691ms.

Add an opt-in observer in ordinary `crates/mir-export` source. Record each
lowered function's preparation and lowering time, exact serialized output hash
before graph transformations, and its corresponding final function hash. Bind
the completed report to the exact program hash. Keep ordinary strict checking,
query order, allocation identity, graph passes and runtime unchanged. Bounds
must reject incomplete diagnostic output. Timings exclude observer hashing
within each function, but remain instrumented diagnostics, not performance
samples. Synthetic adapters and graph passes have separate uncovered costs.

Qualify disabled/enabled/retained artifact identity on the original constant,
static, TLS/HashMap and caller fixtures. Run original assertions against native
Rust and both engines; verify strict errors still reject before publication.
Then run the original token and folded edit histories, including wrong edits
and restored-source rebuilds, in owned caches. Retain each exact artifact and
report. Compare adjacent histories by exact indexed function contents, reporting
identity/order changes separately. Weight repeated output by the observed
function cost instead of just counting functions or bytes. This is a census of
repeated work; it does not prove that the work can safely be skipped.

Before implementing reuse, audit every compiler input consumed by the selected
boundary. MIR or DefPath hashes alone omit type layouts, ABI, instance/shim
identity, compiler/target/options and dependencies. Raw graph-local function IDs,
data offsets, statics, TLS, relocations and allocation alias relationships are
not portable cached values. The reduced edit/revert constant-identity finding
must become an explicit cache invalidation/relocation test, not a deduplication
assumption. Prefer a narrow boundary with complete typed inputs if it captures
enough cost. If it cannot plausibly clear an 8% real-edit screen, choose another
substantial compiler change without running full performance primaries.

Serialize builds, checks and histories under `.work/benchmark.lock`, using
bounded 45-second acquisition. Preserve the 8GiB running floor and all raw
evidence. Use two build workers. No additional archives or private cache cleanup.
Private data stays local, with aggregate-only reports if later included.
