# Trace the changed constant sharing before attempting bytecode reuse

The [preserved Nushell inspection](../../../results/interface-nushell-literal-history-01/assessment.md)
identifies a useful starting point: a second serialized `Expected OneOf` literal,
sixteen extra readonly bytes, and a packed immediate in `test_oneof_deduplicates`
whose low/high halves change from `(224, 14)` to `(368, 14)`. Three original test
branches use that literal. Allocation sharing through rustc's `AllocId` is the
next hypothesis to test. The exporter never iterates its allocation HashMap.

This prepares suggestions 1.4/4.3. The wrapper study has since stopped for
verified futility. The independent worker-count study is active; keep its frozen
workflow/launcher inputs and gates unchanged. Source work on an opt-in exporter
trace can proceed against immutable measured tools. Serialize diagnostic builds
and runs after the active benchmark and its receipt assessment, and do not
change its launcher until the worker experiment releases those frozen inputs.

Add opt-in diagnostic output at allocation requests and materialization. Give
each request its originating function index, complete compiler instance kind,
constant context, and parent relocation edge. Record the compiler allocation ID
as a session-local identifier, whether it was already mapped, the assigned guest
offset, allocation kind/size/alignment/mutability, initialization mask, bytes and
relocations before rebasing. Record relocation byte offsets, relative values and
target IDs. Include static/TLS definitions explicitly; repeated equal static
contents do not establish interchangeable identity. Do not use display names
alone to join compiler shims.

The trace must be bounded and explicitly fail if its diagnostic limit is hit.
It must not reorder requests, coalesce allocations, change MIR, suppress strict
checking, alter execution defaults or change bytecode contents. Trace output and
its compiler/cache/source identities belong in separate diagnostic receipts.
Instrumented timings are not performance samples. Qualify the trace against
existing small constants/relocations/static/TLS cases before a large run, with
byte-identical exported output required when tracing is toggled.

Use the pinned fourteen-test Nushell API case and enough source transitions to
observe original → wrong edit → API edit → original in one new cache history.
Preserve the real tests and wrong-edit rejection. Compare the three literal
references across the original states: do the references receive the same
compiler allocation ID within each export, are any requests cache hits, and at
which request does the additional storage appear? Also check whether two
different IDs describe equal bytes with different origins or relocation edges.
Do not infer a rustc interning/query-cache cause merely from an extra ID.

If this history reproduces the known difference, reduce the relevant constant
references and dependency edit into a small strict-rustc fixture. If it does not,
preserve that negative result and compare the captured compiler inputs with the
original receipts before another attempt. Avoid another broad optimization sweep.

The output is a traced explanation or a narrower unresolved question, not a
deduplication patch. Function reuse will still require compiler/target/feature/
layout/MIR-option dependencies, instance identities, symbolic relocations and
preserved alias relationships. Reusing machine code additionally requires its
ABI and code/data lifetime rules. Equal byte strings or integer-looking
immediates cannot supply those guarantees.


## Implementation and qualification (September 11)

The exporter observes existing allocation requests, cache hits, function
instance kinds/generic arguments, static/TLS definitions, constant/caller/vtable
origins, and each relocation before rebasing. It records initialization bits
alongside raw bytes and does not coalesce, reorder or reuse allocations. IDs are
session-local; function indices refer to the graph before bytecode optimization.
The pinned compiler APIs were inspected in the installed `rustc-src` component,
including allocation init masks and the full GlobalAlloc/InstanceKind variants.

`RUST_INTERP_ALLOCATION_TRACE=1` enables the direct-export diagnostic. Partial
checking and audit mode combinations are rejected. The newline-delimited JSON
trace has a completed footer bound to the bytecode hash. Event and output bounds
are one million records / 64 MiB, with a 16 MiB individual-allocation limit.
A partial record is rolled back and poisons the trace, so limit failures cannot
produce a successful truncated report. Trace completion precedes artifact
publication. The output and Cargo metadata sidecar use `.allocations.jsonl`;
stale standalone diagnostic output is removed with the requested artifact.

Four Rust unit tests cover record boundaries, escaped data, exact byte/event
limits and poisoned failures. The tracked `check_allocation_trace.py` driver
reuses the original scalar-constant, cyclic-static, TLS and caller fixtures,
including every assertion. It will compare old-tool, trace-disabled and enabled
bytecode, and execute thirteen fresh inputs in native Rust and both custom
engines. It validates request/resolution pairs, parent edges, original relocation
bytes, init-mask bounds and artifact binding, and checks three invalid modes.

The [debug workspace check](../../../results/allocation-trace-debug-01/assessment.md)
passes all 272 tests, one existing ignored, including the four new trace tests.
The [release check](../../../results/allocation-trace-release-01/assessment.md)
also passes 272 tests and installs `9bd66cd` / `e965f566`, with unchanged VM and
wrapper hashes. The [original-fixture qualification](../../../results/allocation-trace-fixtures-01/assessment.md)
passes all 383 commands, including byte-identical baseline/disabled/enabled
exports, 52 native and 312 custom executions, and three configuration rejections. Worker measurements use installed tool78 and are unaffected. No launcher
option, large Nushell trace, bytecode reuse or optimization is implemented by this
diagnostic. Keep the launcher frozen until the worker cold study closes, then
run the original/edit/revert diagnostic history above.


The [origin inspector qualification](../../../results/allocation-origin-queries-02/assessment.md)
now verifies exact initialized-byte queries, three references to one original
static, and six equal-content allocations that retain separate identities,
including two mutable TLS values. Ten rejection checks, exact serialized byte bounds and an actual CLI query
pass. `inspect_allocation_origins.py --literal 'Expected OneOf'` can inspect the
future Nushell trace after supplying its matching bytecode and a fresh run ID.
It records all request ancestry and full function instance context, bounds the
query report, and makes no allocation-equivalence or deduplication inference.

The standalone `scripts/allocation_trace.py` transport helper is now
[qualified](../../../results/allocation-trace-transport-01/assessment.md) against
all four original trace artifacts and 33 corrupted-input cases. It validates
regular bounded files, ordered events, strict schema, completion and artifact
binding before a future launcher invocation can execute. The original launcher
is still unchanged; add the explicit flag/capability/environment/receipt path
only after the worker study closes.
