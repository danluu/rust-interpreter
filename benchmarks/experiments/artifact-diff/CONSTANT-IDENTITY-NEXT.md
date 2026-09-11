# Trace the changed constant sharing before attempting bytecode reuse

The [preserved Nushell inspection](../../../results/interface-nushell-literal-history-01/assessment.md)
identifies a useful starting point: a second serialized `Expected OneOf` literal,
sixteen extra readonly bytes, and a packed immediate in `test_oneof_deduplicates`
whose low/high halves change from `(224, 14)` to `(368, 14)`. Three original test
branches use that literal. Allocation sharing through rustc's `AllocId` is the
next hypothesis to test. The exporter never iterates its allocation HashMap.

This is preparation for suggestions 1.4/4.3. It does not supersede the active
fixed-tool wrapper experiment, change its gates, or authorize editing its frozen
inputs. Finish that experiment's required measurements and resource planning
before building or running an instrumented exporter.

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
