# Isolated cross-program staging reuse model

Start from exact adopted Rust/Cargo sources atcc4e767a. Changes are cfg(test) only:
a private model module and a scalar-entry snapshot accessor. No VM option, store,
file format, guest execution or executable publication is added. Same-process
sharing and the register workspace remain parked after failed real-edit gates.

The preceding closed census finds only a modest opportunity. Relative to one
original diagnostic capture, unchanged caller bytes/direct-callee layouts cover
26.9–38.3ms ordinary emission per worker0 and18.1–30.6ms per worker1 for valid
edited artifacts. Those are overlapping associations, not predicted savings or
a full multi-edit cache bound. Large data/immediate and occasional function-ID
changes make naive keys insufficient. Keep all failed measurements and controls.

The model validates structural bytecode once and rejects partial-validation
headers, then binds the checked token to the exact JIT owner. This supplements
the existing strict frontend contract; it cannot substitute for Rust checking.
Identity inputs are the explicit emitter fingerprint/domain, version/target,
function count, heap mode, persistent/scalar options and all test switches,
caller numeric ID and complete serialized Function, direct-callee frame/register/
argument/result layouts and current scalar bytes/step shape/target addresses.
Assertion base is included when the caller contains assertions. Unsupported
profile/tree/stub/nonresumable modes decline. No immediate or address normalization.

This dependency choice follows emit_function_inner, call_slots::collect and
emit_resumable_transition/scalar_call: ordinary analysis reads the complete
caller, transitions read direct-callee layout, scalar transitions read current
ready-entry shape/target, and generated memory operations use the runtime memory
base plus caller operands. Initializer bytes are supplied by each new program.
Exact fresh staging controls test that boundary; it remains test-only.

Stream identity serialization into a4MiB-capped hash sink; bound function ops,
registers and call sites. Retained template payload/capacity is at most64MiB,
including metadata plus declared allocation slack (not allocator RSS). Only a
private freshly emitted CompiledFunction can be captured. Restore checks key,
current code/table budgets, entry/resume bounds and assertion PCs, then rebuilds
assertion references from the current program. This model does not read native
bytes from a file or establish an untrusted-code deserialization contract.

Eight controls cover distinct checked programs, changed data and callee bodies,
body/layout/heap/options/emitter mismatches, assertion rebinding/bases, key/storage/
code bounds, scalar target/admission/step changes, partial/invalid/wrong-owner
inputs, malformed metadata and branches/loops/persistent options. Compare every
machine word, block/resume, assertion and aggregate emission counter with fresh
staging. Require code arenas to remain absent. Test-only diagnostic trace vectors
are not restored; no public profiling mode is admitted.

Run debug/release under the root lock45s with two Cargo/test workers, existing
root build target only, floor max(14GiB,8GiB+2*allocated target),8GiB child/closure.
Close actual terminals and source bindings before further changes. Persistence,
production integration, full correctness qualification and a new genuine-edit
comparison remain separate later stages. Never relax failed gates or rerun an
unchanged parked candidate to seek a favorable sample.
