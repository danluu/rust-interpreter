# Current state — September18,2026

Manual optimization continues indefinitely; the saved goal stays PAUSED.
No goal tools, subagents or independent model calls. Root owns
`/Users/danluu/dev/rust-interp` on `experiment/shared-emission-templates-20260918`.
Private repository: `danluu/rust-interpreter`; push qualified work regularly.

## Current direction

Selective full-width repair is PARKED. Tool6c26c1c8 /VM610a3574 passes
634Rust tests/profile,16ignored;427Pythonpass/22skip;121strict/cache commands;
three exact original profiles. Profile01 had an observer label bug after one
successful guest. Its closed capture was reused in02, which ran only two new
guests and7observer controls. Native layouts/bytes match parked3e53b127 except
validated address immediates at427/532/21scalar sites; all PC arrays match.

The40-command changed-source primary9299/9303 is CLOSED: all outcomes pass;
wall1.011454947,CPU0.998580341,A/Awall0.017814673. Wallmargin1.029269619
fails.1,674evidencefiles/56artifacts verified. No larger history started.
Branch `experiment/selective-narrow-repair-20260918` is pushed throughb3e6a630.
Mainfb5ea729 publishes only its result documentation, preserving all peer
commits through55003f67. No experimental runtime was merged.
[Decision](docs/SELECTIVE-NARROW-REPAIR-RESULT-20260918.md).

Root Rust/Cargo sources are restored exactly to adopted source
`fca687ebac0ea9374a1426addd01169fe707f608`. Do not build the parked variant
or treat its focused tests as controls for a new runtime. Next run a bounded
offline audit of JIT preparation costs from already closed real changed-source
suite receipts. PreparedJit already retains compiled code within each worker.
Measure remaining preparation before proposing cross-process native reuse.
Sum overlapping worker durations honestly; counters are not CPU time or causal
wall savings. No new guest, compiler build or runtime change is needed.
Audit01 is closed after6controls passed and the observer incorrectly required
two workers for the historical one-test private case, which requested one.
Audit02 preserves each original1or2-worker request and adds a seventh control.
The95-receipt audit and7controls are prepared in
`benchmarks/experiments/jit-preparation-costs`, including the incremental parser
and latest primary baseline. Audit02 passes7controls and95receipts under33033/33036, source272e041d.
Its direct closer and named retry69934/69938 both timed out45seconds waiting
for the shared lock; neither reran analysis. Closure03 under60841/60866 succeeds,
binding141inputs,12source files and136evidence files to the original terminal.
Root production source remains exactly adopted.
Median compiler-interval sums are258ms token,73ms folded,4.7ms pgrust,2.5ms
private,15ms Nushell types,214ms parser and255ms recent token. These overlap
across workers and are not promised savings. Next typed identity feasibility
uses saved artifacts; no cache/runtime implementation is admitted yet.
An unexecuted integration-test observer is prepared at
`crates/bytecode/tests/native_reuse_inputs.rs` with7controls and1ignored census.
Its plan is `benchmarks/experiments/native-reuse-inputs/PLAN.md`. It hashes
complete Function bodies plus direct-callee bodies and a conservative program
namespace, preserves numeric IDs, validates full artifacts, and emits no code.
Bounds:128artifacts,128MiB/artifact,4GiB total input,2million function records,
512MiB total output. The controller and chronological analyzer are prepared,
including4Python controls,7Rust controls/profile and1ignored typed observer.
Input census01 is closed after4Python controls and a debug fixture failure:
6pass/1fail/1ignored. TLS offset0 is reserved; the corrected fixture uses16
and separately checks TLS changes with an identical backing initializer.
No saved artifact census or guest ran. The controller now records Python's
original arguments including -B so terminal binding preserves interpreter flags.
Input census02 passes and is CLOSED under24540/24583, source886c94c2:
54artifacts/788MB,194171function records/65.7MB,133transitions/95valid edits,
7Rust controls/profile and4Python controls; no guest. Closure30391/30395 binds
339inputs,223sources and185evidence files. All history median complete-key
stability is zero because the conservative namespace changes on most edits.
Do not interpret this as proof all native code is invalid: initializer contents
may be execution-state inputs rather than emitter inputs. Local-body stability
is65.14%token,68.70%folded,94.19%pgrust,4.95%private,7.39%types,99.95%parser,
61.56%recent token. Some stable callers also invalidate on direct-callee edits.
The next prepared observer is `benchmarks/experiments/native-reuse-scope`:
5controls,133chronological comparisons and two exact original token code pools.
It preserves IDs/heap mode/function count while separating whole-global churn.
The weighted comparisons are original-to-edited, never edited-execution hit
rates. No new artifact census, guest, build or production cache is needed.
Scope01 is now CLOSED under83470/83473:5controls,295inputs,223sources,79evidence.
Median stable body/direct-callee fractions48.68%token,51.81%folded,91.11%pgrust,
4.59%private,4.60%types,99.91%fullparser,42.96%recenttoken. Stable bytecode-op
fractions13.49%token/99.28%parser. Against edited states, original unprofiled
token block/exhaustive arenas retain median11.60%/11.13%bytes under this scope;
NOT chronological cache hits. Adjacent edits2/3can still be highly stable.
Important label correction: internal `nushell-parser-incremental` is actually
pgrust `gram_core` (the original manifest/package proves it). Retain closed
labels/hashes, use pgrust in prose/future work. No data reruns are needed.
Next prototype bounded immutable emission templates shared between suite workers,
which use the same checked Program. Each owner must retain independent native
arena, scalar/assertion relocation, admission and guest state. Begin with
template correctness before production wiring/timing. This is distinct from
the existing per-worker PreparedJit cache; persistent cross-edit caching remains
deferred pending a complete validity/I/O contract.
The Stage1 prototype is now prepared entirely under cfg(test), with precise
assertion/scalar immediate relocation records and6staging controls. Nothing
is connected to guest execution or CLI options. Source module
`jit/emission_templates.rs`; controller/plan
`benchmarks/experiments/shared-emission-templates`. Focused01 passes6controls
per profile under91727/91773, sourcef89ba1e2, and is CLOSED by20954/20958
(verify child in terminal if needed):223inputs,221source bindings,11evidence.
No guest or executable code publication. The full native words/entry metadata
match fresh emission after assertion/scalar rebinding. Next add bounded shared
storage and concurrency/lifetime controls before connecting guest execution.

Candidate audit inputs: the adopted baseline rows (only) from closed
`runtime-composition-edit-{token,folded,pgrust,rg-aot,nushell}-02`, optionally
its incremental parser history and the latest selective-repair primary's
baseline. Candidate45a1529e in the older campaign is REJECTED because the
parser CPUmargin failed1.05; its completed controls remain valid evidence.
Do not mistake the five-project pass for overall adoption.

## Adopted identities

Tool `df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62`
VM `6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf`
Exporter `cf4b3499912506b9ebaed30e6f84e250fccba2d343558dd8cccc847e8a0be96d`
Wrapper `45bca4f272e994bff2564c8f5ccbd7f0d2e52cd4235a3105b4af5764e8ed7fc5`.
Adoption proof `results/scratch-scalar-main-qualification-01/summary.json`.
608Rusttests/profile13ignored;121strict;726five-project commands plus both
88parser guards and114parser compatibility. This remains a selected-function/
test-body engine; complete application thread, unwind and OS support is absent.

Current-host original adopted profile controls are mode=control rows in
`results/runtime-composition-profile-02/summary.json`. Older profiles predate
18CPU-feature instruction drift. Fresh normal-entropy native samples are closed
in `results/adopted-current-runtime-sampling-02`:1,933/1,429 generated samples,
zero unassigned. Preserve every successful capture without reruns.

## Recovery and ownership

- Builds, tests and substantial analysis serialize with `.work/benchmark.lock`,
  `acquire_lock(lock,45)`. Two Cargo/test workers. Only root target is
  `.work/fixed-frame-clear-combined-build-01/target`; NEVER clean it.
- Build floor max(14GiB,8GiB+2*allocated target); analysis12GiB; children8GiB;
  primary14GiB; closures8–10GiB as declared. Current free space about23GiB;
  admit every stage freshly. Nushell real six-cache reservation is about47GiB.
- Independent cleaner read-only status:
  `/usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status`.
  Do not repair/restart/compete with it. Never control any peer process/session.
- Compiler/Cargo/frontend and application-admission work belongs to peers.
  Preserve their worktrees. Root publication worktree `.work/publication-main`
  is clean atbb0d32f0 on `integration/guarded-local-facts-main-20260913`; fetch
  before publishing, preserve peer commits and never force push.
- No AWS activation/purchase/model/billing fallback and no browser.
- `suggestions.txt` is user-owned/untracked, SHA256
  `4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f`,
  reread unchanged. [Dispositions](docs/SUGGESTIONS-REVIEW-20260913-1245.md).

## Preserve closed work

Conservative implicit-zero3e53b127 failed its wall gate; selective6c26c1c8 also
failed. Shared-cold-tail8bce082f failed wall/CPU despite smaller code. Native
frame pairing and consumer-only high-word census had too little sample coverage
and were deferred without timing. Indirect/readonly/successor45a1529e passed
726cases then failed the parser CPUmargin; repository parser never started.
Do not repeat unchanged candidates or relax gates. All exact branches and
closure paths are in the [previous detailed state](docs/history/STATE-20260918-before-preparation-census.md)
and [earlier state](docs/history/STATE-20260918-before-cold-tail-primary.md).

Exact completed public cache retirements are closed: old scratch/scalar
Nushell custom; runtime-composition token/folded custom+native; current
composition Nushell custom. Old repository-parser retirement found zero files.
Do not repeat these. Preserve all executables, tools, RBC/catalogs, proof data,
private caches, shared target and peer work. Current Nu native/check caches
remain, and require fresh exact ownership/protection audit before any retirement.
