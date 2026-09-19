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

## Model02: explicit relocations across checked programs

Keep all eight strict controls and add four rebinding controls. The emitter
records scalar-target and assertion-code immediate spans under cfg(test), with
the scalar callee and exact caller PC, or the local assertion index. The model
requires sorted, nonoverlapping, one-to-four-word spans, original immediate
encodings and associated BLR instructions. Compare the full ordered set against
every current eligible scalar Call and every assertion; incomplete or duplicated
ledgers decline. Capturing also requires the original owner's actual targets and
assertion codes. This remains trusted in-memory staging, not a native-file trust
or authenticity check.

A separate keyed mode omits only scalar target addresses and the assertion base.
All caller operands, numeric callee IDs, layouts, scalar admission and step/byte
shape, options and checked-owner requirements remain. Restore patches only the
recorded spans, requires identical instruction widths, keeps branch positions
fixed, and rebuilds assertion strings from the current Program. A width change
declines. The ledger is charged within the unchanged64MiB retained-storage cap.

New controls compare all words and metadata across distinct programs, multiple
calls/callees and assertion bases, and round-trip recapture. They cover width
changes, missing/overlapping/wrong-site/wrong-callee/wrong-immediate ledgers,
body/layout/admission/step changes and exact/insufficient code budgets. Require
all arenas to stay absent. The two profiles now each expect12 focused tests.
Close this run before modifying the sources; no production integration, native
execution, storage, guest commands or timing claim follows from these tests.

## Saved parser replay

Model02 passed12 controls/profile and is closed before this addition. One
explicit ignored release test now reads the same eight SHA-bound parser artifacts
and the fully validated original preparation capture. Select only functions with
published ordinary entries in that original capture, separately by worker; bind
their original numeric IDs, names, operation counts and full Function hashes.
Retain original templates under an aggregate64MiB per-worker charge. Compare
each original template against the other seven checked artifacts, including the
wrong-result edit and independently lowered restored-source artifact. A key miss
or width/budget decline is recorded; every successful restore must match fresh
staging word-for-word and in all relevant metadata. No arena is allocated.

Scalar entries are modeled from current proof/lowering in ascending callee order
with existing proof/work bounds, using synthetic addresses. This deliberately
does not reproduce original runtime admission order or code-arena usage, and
cannot establish a production hit rate. Original trace metadata selects bodies;
the replay is a correctness/coverage diagnostic for the new model, not a guest
run or a source-edit benchmark. No warmed history store or file cache is added.

Record single diagnostic key-all, restore-key-match and fresh-exact intervals.
Restore already includes a key computation; these intervals must not be added
or subtracted into a predicted command saving. The cfg(test) emitter records
relocations, and these runs exclude disk-cache loading, publication and misses'
fresh emission. Associate exact IDs with the existing original ordinary-emission
intervals only, preserving the earlier trace's nesting/overlap limitations.
Require the complete input/output/source/terminal closure before further work.

## Model03: bounded populated history

The original-only replay is closed before this change. Add a private64MiB
history keyed by the already-qualified identity, with one ordered recency record
per template and at most16,384 entries. Charge each template plus256 bytes of
map-node slack and512 bytes base bookkeeping. This is declared retained payload,
not allocator RSS. Oversized entries and timestamp exhaustion decline without
eviction; replacement removes the prior entry's charge. Evict the least recently
used entry only when a new bounded entry needs space. No disk/IPC API is added.

Two additional controls bring focused qualification to14/profile: bounded
recency/replacement/eviction and exact reuse of two checked caller-body variants
across four distinct owners with different assertion bases/scalar addresses.
Repeated hits must not grow metadata. Close these controls before running the
saved-artifact replay that populates the history after misses.

The first history-model admission (Model03 at153e3057) timed out on the shared
lock before creating a stage directory or starting any build/test. Its exact
terminal/controller bindings are preserved in results/cross-program-template-model-03.
Model04 retries only that unstarted14-control qualification under unchanged
source semantics, worker count and disk/lock gates. Do not repeat any earlier
completed model or saved-artifact replay.

While the peer lock remains held, the history replay driver is implemented but
not run. Model04 compiles that ignored diagnostic alongside the14 controls;
history.py requires its completed passing closure before admission. This adjusts
implementation order only; qualification still precedes the actual replay.

The populated replay retains the exact same eight input artifacts and fixed
original numeric function sets as Replay01. Visit each function once in ascending
ID order per state, including original seeding and the wrong edit. On each miss,
freshly stage and capture the current variant; charge and evict under the same
64MiB cap. Every hit must equal fresh staging. Record missing function IDs,
key/restore misses, insertion/emission/capture declines, evictions and current
entry count/charge. No later execution reachability or admission order is claimed.
Do not associate a newer cached variant with the old function's preparation
interval: names/bodies at a numeric ID may have changed. Report diagnostic
lookup/restore, fresh and capture/insert intervals separately, with no command
speedup calculation. Native file/IPC storage and publication remain absent.

## Model05 and History02: bind identity once per operation

Model04 and History01 are closed before this change. History01 restores every
hit exactly, but computes identity both before lookup and inside restore/capture.
Introduce a private Request containing the computed key, exact immutable JIT
borrow, function ID, emitter and mode. Restore accepts that request directly;
callers cannot pair a standalone digest with another owner. Request emission
produces an Emission tied to the same request, so the new capture path obtains
both metadata and code from that exact operation. Immutable borrows prevent
intervening owner mutation. Legacy wrappers remain for the prior negative tests.

Two new controls bring qualification to16/profile: exact cross-owner emission/
restoration/recapture, and foreign checks/functions/modes/emitters plus code and
storage bounds. After closure, History02 uses the bound request through lookup,
restore and capture on the same saved input. Prior History01 proved these input
keys fit unchanged limits; the new replay explicitly requires that property.
Preserve the older diagnostic rather than treating either single interval run
as a statistical timing comparison. No production cache or native publication.

## Model06: explicit native publication fixtures

Model05 and History02 are closed before this extension. The first16 controls
still allocate no code. Add two macOS/AArch64 controls that deliberately prepare
real scalar callees, restore ordinary staging, and publish through the existing
finish_preparation path. Keep the source owner alive so its scalar address is
distinct from the current owner's. Require actual reuse to occur, compare with
fresh staging before publication, then compare execution with fresh JIT output.

One control changes the callee result and current data initializer independently;
both appear in the128-bit returned value. The other covers passing/failing
assertions, instruction budgets0–20, frame limits1–3 and memory limits128/4096,
including repeated executions with fresh guest state. Width/key declines retain
ordinary fresh emission. Compare success values/logical instruction counts and
exact errors, including the current assertion message after rebinding its base.
The focused run now expects18 controls/profile and explicitly records native
fixture execution/publication. Original-project guest commands remain zero;
this is correctness qualification, not a runtime cache or an end-to-end result.
