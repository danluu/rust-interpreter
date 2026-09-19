# Current state — September18,2026

Manual optimization continues indefinitely; the saved goal stays PAUSED.
No goal tools, subagents or independent model calls. Root owns
`/Users/danluu/dev/rust-interp`, branch
`experiment/shared-emission-templates-20260918`, private repository
`danluu/rust-interpreter`. Push qualified work regularly; do not stop at a milestone.

## Current experiment

Shared immutable emission templates between prepared suite workers, explicit
`--jit-shared-templates`, default OFF. This is different from existing per-worker
PreparedJit reuse and does not introduce persistent native files or skip checking.
Owners borrow the same checked Program but keep independent native arenas,
scalar admission/budgets/targets, assertion indices and all mutable guest state.
Ordinary finish_preparation alone publishes rebound code. Rebinding that would
change immediate instruction width misses. Store retains at most64MiB with one
variant per numeric function ID, short mutex operations and poison/full misses.
One effective worker uses ordinary preparation. Counters are hits/misses/restored
bytes, never a claim of time saved. Compiler intervals include cache overhead.

Stages1–3 are CLOSED:6/12/17 focused controls per profile, including exact native
words/entry metadata and real separate native arena execution with budgets,
faults, static/TLS reset, fallback, concurrency and scope controls. Stage4 adds
production API/CLI/lazy path and bounded capture. Focused04 never acquired lock;
closed43862/43905. First closer89522/89598 also timed out. Focused05 controller
syntax failed before admission; closed before correction. Focused06 under
72299/72302 passes16Python controls then compile-fails an old test closure because
Mutex makes Jit invariant. Closed83483/83595 before adjusting the test to read
its function through jit.program; assertions unchanged. Focused07 under2155/2173
passes20Rust controls/profile, reuses the16closed Python controls and retains a
non-test release VM; closure38245/38249. Every attempt remains in results.

Full build01 under52151/52154 passes635Rust tests per profile,14ignored, and
434Python tests/22skipped (456discovered). Exact retained VM installed with the
unchanged adopted exporter/wrapper. Closed by40140/40144.
Tool `7a4e2bc034fc55c0ca89e174b0d403d0af8174eb8046443e09b11311d52af4ca`.
VM `d071c9123c40cd9ee9ad4dd1bb13faed046373a7d743ebc85919b08c029e8ebd`.
Build sourcef90e816e, runtime sourceef50023f; setup105.17s plus focused28.02s.
Strict qualification121 commands passed under56495/56498 and is CLOSED by
61762/61805: native/reference/cache agreement, unreachable type/borrow errors,
actual partial artifact rejection and source restoration all pass.
Suite01 passes13 commands under67799/67802 and is CLOSED75018/75021.
All114 original parser outcomes and wrong-edit failures match. Actual two-worker
sharing records797hits/3,799,956restored bytes (37,929,344charged store bytes)
on original,53hits/151,512bytes on wrong source. One-worker and private one-entry
fallback stay inactive; all six invalid/partial modes reject before execution.
No performance command has run for this candidate.
No template runtime has been merged to main.

Completed suite.py/close_suite.py: six full pgrust parser
runs (original/wrong edit × ordinary-two/shared-one/shared-two), one private
rg-aot one-entry run and six mode/partial rejection commands. Actual shared hits
must occur on both parser states before timing; zero hits cancel timing, not
trigger reruns. All114 original parser assertions/outcomes stay intact. Saved
original artifacts are bound to prior closed native histories; ordinary entropy.

The primary protocol is CLOSED:82684/82688 (see terminal for exact child)
passes19controls; closer89745/89793 binds492inputs. The primary is prepared in
`benchmarks/experiments/shared-emission-templates-screen`:32commands,8states ×
4rotating modes (native/adopted/adopted duplicate/candidate). Five valid edited
pairs only enter the wall/CPU gates; anchors, wrong edit and restoration remain
mandatory. Full native/custom workflows,2Cargo workers/2native test threads/
2suite workers, ordinary entropy. Require24GiB initial/8GiB child disk admission.
Its19protocol controls and original-source schedule have passed and closed. Primary choice was
frozen before candidate timing; gate and qualification contract in
`benchmarks/experiments/shared-emission-templates/QUALIFICATION.md`. A failed
wall or CPU gate cancels larger comparisons; do not retime unchanged failures.

## Why this direction

Closed jit-preparation-costs02 audits95saved adopted changed-source receipts:
compiler-interval medians258ms token,73folded,4.7small pgrust,2.5private,15types,
214full parser,255recent token. These worker durations overlap and are not CPU
or critical-path savings. Input census02 checks54artifacts/194171function rows;
namespace changes invalidate the conservative whole-program keys on most edits.
Scope01 separates that churn: original-token arenas retain only11.60%/11.13%
body/callee-stable bytes; parser bytecode-op stability99.28%. These are bounded
identity ceilings, not actual hits or savings. Persistent cross-edit reuse is
deferred; sharing the exact immutable Program is a narrower first contract.

The old internal label `nushell-parser-incremental` is WRONG: it is pgrust
`gram_core`. Retain closed hashes/labels but use correct prose/future names.
Actual Nushell type-relations is a different case. All audits closed and pushed;
preparation-cost documentation/results are on mainbb0d32f0. Scope details,
identity controls, old ownership and every failed stage are archived in
[previous state](docs/history/STATE-20260918-before-shared-template-qualification.md).

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
  primary14GiB; closures8–10GiB as declared. Current free space about27.5GiB;
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
private caches, shared target and peer work. Current composition Nu native_lines and native caches are now selectively
retired (closed-composition-nushell-{native-lines,main-native}-retirement-01),
71,976nonexecutable intermediates each; every8,659protected hash unchanged.
The two runs recover about3.65/5.41GiB free respectively (not their logical
8.0/17.3GB totals). Do not repeat them. Only the current Nu check cache remains
for a future exact ownership/protection audit if needed.

Next launch shared-emission-templates-parser-screen-incremental-01 with the
closed32-command protocol after a fresh24GiB admission. All runtime/suite/
protocol inputs are fixed; no successful command needs repeating.
