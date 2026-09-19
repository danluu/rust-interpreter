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
