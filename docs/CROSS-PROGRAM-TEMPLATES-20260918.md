# Cross-program native staging model

The custom emitter can reuse exact staging across distinct checked Programs
when the complete caller and relevant emission inputs match. This is a test-only
primitive, not an adopted runtime cache or an end-to-end speedup.

The initial eight controls pass in debug/release. The extension passes12 per
profile, including explicit scalar-target and assertion-code relocations.
Every successful restoration matches freshly emitted words, block/resume tables,
assertions and emission counters. Assertion strings come from the current Program.
The complete current caller, direct-callee layouts, scalar admission/byte/step
shape, runtime options, target/version and explicit emitter fingerprint are
identity inputs. Strict mode also binds scalar targets and assertion bases.

Rebinding mode excludes only those two owner-dependent values. The emitter
records each actual immediate span with its callee/caller PC or assertion index.
Capture checks the original values, sorted nonoverlapping spans, encodings,
associated scalar BLR and complete expected site sequence. Restore regenerates
only those immediates and requires identical instruction widths. Other changed
immediates remain key misses. Wrong bodies/layouts/admission, missing or malformed
sites, width changes and insufficient budgets decline before publication.
No executable arena is allocated in these controls.

Identity serialization is streamed under4MiB, with bounded operations/registers/
calls. Retained template payload/capacity and allocation slack are charged under
64MiB. This is not a bound on allocator RSS, and the trusted in-memory primitive
does not establish authenticity for a future native-code file format. Structural
validation supplements the unchanged strict Rust frontend; it does not replace
type or borrow checking.

[Strict model](../results/cross-program-template-model-01/summary.json),
[relocation model](../results/cross-program-template-model-02/summary.json),
[plan](../benchmarks/experiments/cross-program-template-model/PLAN.md).

The saved parser replay now covers all seven transitions from the original
artifact, including the deliberately wrong-result edit and independently lowered
restored-source artifact. It selects the original capture's2,391/1,154 functions
with ordinary entries in workers0/1. All are captured within32,632,316 and
16,974,468 retained bytes. For valid edits,1,221–1,512 and601–817 original templates
restore exactly; the rest are identity misses. No matching key fails relocation,
and every successful result matches fresh staging.

The scalar table is modeled with fresh current-program proof/lowering, ascending
callee order and synthetic addresses. It does not reproduce runtime admission
order or aggregate code-arena pressure. The fixed original function set also
does not measure which functions later edited executions reach. These counts
are exact-model coverage, not a production cache hit rate.

The matching IDs associate with27.4–38.8ms of original ordinary-emission intervals
in worker0 and18.6–31.1ms in worker1. In this separate diagnostic replay, hashing
all selected keys takes about9.2–9.6ms and5.4–5.6ms respectively for valid edits.
Restore includes its own key computation, and test-mode emission records the
relocation ledger. These intervals cannot be summed or subtracted into a command
speedup; disk/IPC loading, native publication and misses' fresh emission are
absent. [Closed replay](../results/cross-program-template-replay-01/summary.json).

The modest original-only coverage makes a production cache premature. Next test
a bounded populated history across the same actual artifacts. That asks whether
retaining newly emitted variants meaningfully changes reuse, while still
checking every restored result against fresh emission. Keep the original-only
result intact. Any subsequent production implementation must measure complete
changed-source commands against the adopted engine and ordinary native Rust,
including lookup/storage/startup costs and all existing correctness guards.

The populated-history model now passes14 controls/profile and the full saved
history. The first qualification admission timed out before any test; that
terminal is retained. The successful replacement admission and replay are closed.
Every hit still equals fresh staging. For valid edits1–5, exact counts are:

| Worker / fixed original function set | Edit1 | Edit2 | Edit3 | Edit4 | Edit5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 /2391 |1512|2389|2389|1221|2000|
| 1 /1154 |817|1152|1152|601|973|

Worker0 reaches the64MiB charge limit and evicts447,479 and635 entries in edit4,
edit5 and restored-source state respectively. Worker1 finishes with2,230 variants
and40,978,712 charged bytes, without eviction. No capture, emission or relocation
declines occurred in this modeled history. These are fixed original numeric
function sets visited in ascending order, not later measured guest reachability.
The changed functions at a numeric ID cannot inherit that ID's original timing.

This materially improves coverage over original-only reuse on edits2,3 and5,
so the original-anchor counts should not be treated as a populated-cache ceiling.
It still does not establish a command speedup. The diagnostic currently hashes
each requested key and hashes it again inside restore; misses also hash during
capture. A production interface should bind one checked key to the immutable
current owner/function/options for that operation, then use it for lookup and
restoration without weakening validation. Persistent storage or IPC must earn
its loading, serialization and startup cost in real edited-source comparisons.
[History controls](../results/cross-program-template-model-04/summary.json),
[populated replay](../results/cross-program-template-history-01/summary.json).

The bound-request implementation passes16 controls/profile. Its populated replay
matches all16 worker/state rows from the previous history in outcomes, inserted
and evicted entries, native word counts and retained charge. One private request
holds the computed identity and an immutable borrow of the exact current owner;
the capture path receives emission tied to that request. The replay's separate
lookup/restore intervals are now roughly1.1–2.9ms for worker0 and0.6–1.6ms for
worker1 on valid edits. These single diagnostic runs still establish no end-to-end
speedup. [Bound-request replay](../results/cross-program-template-history-02/summary.json).

Real native publication is also qualified by18 controls/profile. Two additional
fixtures keep the source code owner alive, rebind to distinct current scalar
addresses, publish through the existing JIT path and execute the current callee
and current data initializer. Results match both fresh JIT and interpreter
values/instruction counts. Other cases compare exact fresh-JIT outcomes over
instruction budgets0–20, frame limits1–3, memory limits128/4096 and passing/failing
assertions, including repeated fresh guest states and current assertion text.
The initial native fixture mistakenly read null address0; the fresh control also
failed. That debug failure is closed, release remained unstarted, and the corrected
fixture uses valid address8. [Native qualification](../results/cross-program-template-model-07/summary.json),
[preserved fixture failure](../results/cross-program-template-model-06/summary.json).

The test-only context now runs through normal lazy preparation, preserving fresh
scalar proof/admission and ordinary publication. It passes20 focused controls in
both profiles; the broader workspace passes628 tests/profile with15 ignored.
The actual parser replay then executes114 test bodies over eight saved states,
with reuse disabled and enabled:1,824 invocations. All expected outcomes match,
including8 passes/106 failures for the deliberately wrong edit and114 passes for
every other state. The16,301 restored function templates all match fresh code and metadata
before publication. No matching template fails restoration.

Actual scheduling matters: workers exchange the larger share of reached
functions on edits2 and3, unlike the earlier fixed-function replay. Aggregate
hits/lookups for valid edits1–5 are2,185/3,598,2,326/3,658,3,547/3,597,
1,877/3,640 and2,597/3,632. Each valid worker/state has one key decline and one
ordinary JIT decline; this observation alone does not identify their reason.
Worker0 ends with1,948 cumulative evictions; worker1 has none. Retained charges
stay within64MiB per worker. This establishes actual reachability and execution
correctness for these states, not a production hit rate or command speedup.
[Real-suite replay](../results/cross-program-template-suites-01/summary.json),
[verifier controls](../results/cross-program-template-model-09/summary.json),
[workspace checks](../results/cross-program-template-workspace-01/summary.json).

Next move the qualified primitive behind an explicit experimental feature and
give a caller ownership of the bounded in-memory history across checked Programs.
Keep normal builds and default preparation unchanged. The intended command-level
candidate is an explicitly started local execution session: retain only trusted
staging templates in memory between commands, build/check every changed source
normally, and recreate native owners and guest state for each request. This avoids
loading executable cache files and supplies a concrete route to cross-command
reuse. Transport, setup, hashing, validation, misses and all session CPU must be
included in the changed-source comparison; a session without reuse is an
additional mechanism control, alongside adopted fresh-process and native commands.
No production cache is enabled yet.


The experimental `jit-template-session` library feature now passes633 workspace
checks in both profiles (16 explicit diagnostics ignored). Public API controls
exercise real non-test-library emission, changed callees/data, limits and current
assertion text, invalid/partial Programs, full storage and dropped original owners.
Ordinary and feature release VMs are retained. No default runtime is adopted.
[Closed API qualification](../results/cross-program-template-session-api-04/summary.json).
Earlier startup, ignored-count bookkeeping and feature configuration failures
remain preserved; completed successful commands were retained through correction.

An inherited-pipe session is now under qualification, with per-request environment
snapshots and explicit input/report bindings. A negative wire test found serde's
unit-variant handling accepted extra Shutdown fields; the corrected variant keeps
that rejection test. Saved-project session replay and command-level transport
remain required. [Transport design](TEMPLATE-SESSION-TRANSPORT-20260918.md).
