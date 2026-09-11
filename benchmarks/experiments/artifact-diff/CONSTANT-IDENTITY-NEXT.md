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

## Launcher integration after the frozen worker study

Add an explicit `--allocation-trace` flag to `scripts/interpreter.py`. Reject
audit combinations before any tool build or Cargo invocation; require the
installed exporter's `allocation-trace` capability. Set the already implemented
`RUST_INTERP_ALLOCATION_TRACE=1` only for that request. The exporter tracks this
environment input for the selected Cargo unit, including transitions back to
disabled. Do not change the workspace identity or any guest engine defaults.

After Cargo selects its exact `.rmeta.rbc` sidecar, call `selected_trace` while
the invocation lock is still held, before starting the VM. Report the trace's
path, byte length, SHA256, event count and artifact binding in an explicit
diagnostic receipt, including when ordinary timing statistics are disabled.
Do not fall back to the standalone `program.rbc` diagnostic if the selected
Cargo sidecar is missing or invalid. Leave the disabled path free of trace reads.

Qualify this against a fresh owned Cargo fixture using the unchanged original
constant fixture assertions and immutable tool `e965f566`. Exercise disabled →
enabled → unchanged enabled → disabled → enabled in one cache namespace; compare
artifacts and results at each step. Preserve an enabled sidecar, then damage its
footer or remove only that selected sidecar while Cargo considers the source
fresh: both must reject before VM execution. Restore the exact saved file after
each probe. A stale standalone diagnostic must not rescue either rejection.
Check unsupported historical tools and audit combinations before Cargo starts.
Rerun the original launcher regression assertions with the immutable new exporter
and historical tool routing. This is validation, not a no-op speed benchmark.

Then run the fourteen-test Nushell original/wrong/API/original history, preserving
each selected trace/artifact pair and checking original wrong-edit failures and
source restoration. Query the literal's three original references and first extra
materialization using the qualified origin inspector. No function-reuse patch
should precede this attribution or ignore the measured ~71-ms lowering interval
within the ~5.3-second warm command in this particular case.


The worker study closed at its predeclared CPU failure bound; its measurements
remain unchanged. Launcher integration now exposes the explicit flag, validates
Cargo's selected trace under the invocation lock, and reports exporter/artifact
identities even without timing statistics. [Qualification02](../../../results/allocation-trace-launcher-02/assessment.md)
passes 17 commands and five traced observations. Qualification01 failed before
fixture creation due to a driver return-shape assumption; that failure is retained.
The [original 99-check regression](../../../results/allocation-trace-launcher-regression-01/assessment.md)
also passes, plus separate historical-tool execution. The tracked
`trace_nushell_history.py` driver is prepared but not yet run.


## Actual Nushell attribution and next reduction

The [four-state history](../../../results/allocation-trace-nushell-history-01/assessment.md)
passes all eight native/custom commands with original assertions and restoration.
[All four origin queries](../../../results/allocation-origin-nushell-history-01/assessment.md)
reproduce and match historical bytecode. The three panic strings share one
compiler allocation in original/wrong states; the API edit splits the literal
in `test_oneof_deduplicates`, retaining that split after source restoration.
The split exists in the compiler IDs before exporter layout.

Next reduce this to three functions referring to the same panic string, with
only one function calling an API changed from a concrete argument to `impl Into`.
Use dynamic scalar input so the panic branches survive MIR construction. Keep
all workload assertions unchanged; include an intentionally wrong API body
that reaches those assertions, then the API edit and exact restoration. Compare
fresh, separate custom Cargo histories with `CARGO_INCREMENTAL=1` and `0`, retaining
all trace/artifact pairs and native assertion controls. This is a causal diagnostic,
not a performance benchmark. Record a negative result if the split does not recur.

The prediction is one/one/two/two allocations with incremental reuse and one in
each state without it. That would support the mixed decoded/recomputed MIR
mechanism found in the pinned compiler source; individual query reuse still
needs direct evidence before being asserted. Do not patch allocation equality
or adopt function caching from this reduction alone.
