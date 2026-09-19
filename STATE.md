# Current state — September18,2026

Manual optimization continues indefinitely; the saved goal remains paused.
Root owns `/Users/danluu/dev/rust-interp` on
`experiment/selective-narrow-repair-20260918`. No subagents or independent model calls.
Private repository: `danluu/rust-interpreter`. Push qualified work regularly;
never merge an entire experimental branch over concurrent main changes.

## Current experiment

The shared complete cold fault-tail candidate is **experimental**, tool
`8bce082f179ce3b9c29bf7c26588ace603b252e5fd20b348779da0a936571d36`, VM
`93b75492f725a41750f2da8b05dfd09c61bb22379b4ddfa67c422fa06f8cceff`.
It retains the adopted exporter `cf4b3499` and wrapper `45bca4f2`.
Only identical complete position-independent fault returns inside one resumable
function share a retained tail through a local B instruction. Assertions,
budgets, successor fallbacks, scalar bodies and logical operations stay intact.
Strict type/borrow checking still finishes before any guest execution.

Closed qualification:
- Bounded census and exact reconstruction:1,050/1,245 ordinary functions and
  60/69 scalar bodies in two retained captures.720,192/837,504bytes saved;
  only duplicate fault tails and required branch offsets change.
- Five focused native controls in debug/release, including complete state and
  callee-saved ABI equality with the unshared emitter. Earlier fixture failures
  remain archived; they exposed two incorrect test assumptions.
-615 Rust tests per profile,14 ignored;427 Python tests pass,22 skipped.
-121 strict/cache commands pass, including unreachable type/borrow rejection
  and actual partially checked artifact rejection before scalar execution.
-Three new original-test profiles match current-host adopted controls at every
  original PC, memory peak, entropy and scalar execution count. No JIT declines.
-13 primary protocol controls plus3 map controls; exact full Python build
  evidence reused through source/log bindings, not reported as fresh tests.

**Closed:** `shared-cold-tail-screen-token-01`, source9ecb65d9,
supervisor97059 / child97170, normal completion. All40 outcomes and source
restoration pass, but performance gate fails: wall1.025596964, CPU1.014945602,
A/A wall3.607767%, CPU3.375373%. No gain established; larger histories cancelled.
The closure verifies1,674 evidence files and56 artifacts. Never repeat this
candidate unchanged. Main retains the adopted VM.

The private host-frame access census is also closed:6 controls,87 frozen inputs,
zero guest/build commands. Potential pairs cover only9/1,933 and9/1,429 generated
self samples. Defer this mechanism without a runtime prototype or timing.
[Decision](results/native-frame-access-census-01/ASSESSMENT.md).

The typed high-word consumer census is closed in01 and02. The expanded masked
integer proof passes8 controls/profile and6 traffic controls, including3,800
actual integer-semantic comparisons. It covers33/1,933 and13/1,429 upper-store
samples. Defer a consumer-only emitter; both studies and sources are retained.

The implicit-zero census is closed:7commands,7Rustcontrols/profile and6traffic
controls;126/1,933 and119/1,429 eligible native samples;6.54M/8.51M conservative
interpreter read repairs. This admitted a bounded runtime prototype.

Current candidate: implicit-zero private register upper words. Only resumable
functions use it; all initialization remains. Native high reads and persistent
reloads synthesize zero, narrow raw high stores are omitted, and every
interpreted read is repaired using the active function's published proof.
Proof bytes are capped at8MiB; declines retain full representation. Ordinary
native/tree modes allocate no proof table. Scalar bodies are unchanged.

Focused01 retained6passes/1fixture failure (insufficient reads for persistent
assignment);02 passed9tests/profile. Review strengthened03 to force a wide
value into actual backing before frame reuse.03 passes9/profile, including
poisoned slots/large offsets, host ABI, TLS and indirect handles, all budget
prefixes, exact profiles and re-emission after metadata exhaustion. Closed
source5d4b1c5c, supervisor63791/child63794. No timing result or adoption exists.
The full build now passes628Rusttests/profile,15ignored and427Pythonpasses/22skips.
Source d7de70da, supervisor91817/child91860,4commands,111.4seconds of setup.
Isolated tool3e53b127220f71115eec7b18e2ed452577471ab48cfd5d4c669c0ae3a295f32a,
VM8e369c0f3a6f6fd0b793372d27c26f4848db8536f4cb8bfcf8672b0d0a12ca72,
unchanged exporter/wrapper. The first evidence-closing command timed out45s
waiting for peer compiler-build PID92782; all build commands remain successful.
Closure retry74141/74168 now passes461frozen inputs/450Git bindings without
repeating a build command. Strict121commands now pass (93897/93900), and3new
original profiles match adopted controls at every PC, memory peak and entropy
(8078/8081). Maps reconstruct exactly, scalar bodies/counts remain unchanged,
zero declines. Native bytes11,952,720→11,687,140;14,508,196→14,198,260;
1,978,352→1,916,484. These are correctness/code-size results, not timing.
The primary protocol passes13+3controls (30396/30399) and reuses exact449Python
build checks. The40-command primary is now closed and fails the wall gate: ratio0.978171695,
A/A0.043579437, margin1.021751132. CPU0.986097055/margin1.026384095 passes.
All outcomes/restoration/artifact identities pass.36363/36366 finished normally;
1,674evidencefiles/56artifacts verified. Park3e53b127 unchanged; no larger
histories started. Next census selective full-width interpreter repair costs
from retained typed/current profiles, before any different runtime variant. Controllers are in
`benchmarks/experiments/implicit-zero-storage-workflows` and
`benchmarks/experiments/implicit-zero-storage-screen`.
[Contract](docs/IMPLICIT-ZERO-REGISTER-DESIGN-20260918.md),
[focused](results/implicit-zero-storage-focused-03/ASSESSMENT.md).

The selective-read diagnostic is closed at330ac583:7commands,11controls/profile,
234frozen inputs. Actual candidate/adopted interpreted-PC arrays are identical.
Required repairs fall6,542,145→1,033,563(block) and8,513,802→843,810(exhaustive),
mostly checked indirect handles.96poisoned actual-interpreter heap comparisons,
alias/checked-helper/width controls pass. No original guest was rerun.

Current new variant moves that exact classifier into production and repairs
only full-width interpreted consumers. Native emission/proof admission stays
unchanged from parked3e53b127. Add2native/VM controls for low-only backing and
heap fallbacks followed by full reads; focused stage expects15controls/profile
(11native/VM +4role), then634workspace tests/profile/16ignored. No new tool is
installed or timing admitted yet. See `benchmarks/experiments/selective-narrow-repair/focus.py`
and `docs/SELECTIVE-NARROW-REPAIR-20260918.md`. Main ccb3b465 contains only the
closed conservative-primary outcome; root owns this new experimental branch.

[Build](results/shared-cold-tail-build-01/ASSESSMENT.md),
[strict/cache](results/shared-cold-tail-qualification-01/ASSESSMENT.md),
[profiles](results/shared-cold-tail-profile-01/ASSESSMENT.md),
[primary protocol](benchmarks/experiments/shared-cold-tail-screen/SCREEN.md).

## Adopted runtime and prior decision

Main retains scratch/scalar tool `df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62`
/ VM `6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf`.
Archived source `fca687ebac0ea9374a1426addd01169fe707f608` is the isolated
cold-tail baseline. All Rust/Cargo inputs were restored exactly to it before
applying this candidate; rejected experiments remain in Git history.

The previous indirect/readonly/successor composition45a1529e is **rejected**.
Its40-command primary and726-command five-project comparison passed, but the
88-command matched incremental parser history failed the unchanged CPU margin:
1.0054002208 +0.0448177645 =1.0502179853 >1.05. All assertions still passed.
The repository-parser history and runtime integration were cancelled/unstarted.
Do not rerun it or change its gate. Outcome documentation was published to main.
[Decision](docs/RUNTIME-COMPOSITION-20260918.md).

Main1dec3a58 separately publishes the qualified `Untagged`/`VM_ALLOCATE`
vmmap parser repair. The current macOS label caused the first sampling study to
miss its arena; no sampler ran there. Fresh sampling02 succeeded and is closed:
1,933/1,429 generated self samples fully attributed. Both successful guests must
be retained without repeats. These are diagnostic windows, not timing results.
[Captures](results/adopted-current-runtime-sampling-02/ASSESSMENT.md).

Current-host adopted profile controls are **mode=control** rows in
`results/runtime-composition-profile-02/summary.json`; its candidate is rejected.
Older dynamic profiles predate verified CPU-feature drift. Never substitute
old counts or compare new-host candidate to those old controls. Entropy replay
is limited to correctness profiles; all end-to-end timings use normal entropy.

## Recovery, ownership and resource boundaries

-Read-only status of the independent cleaner:
 `/usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status`.
 Do not repair, restart or compete with it. Recent free space is about23GiB;
 admit every stage freshly, never assume headroom persists.
-Builds, tests and substantial analysis hold root `.work/benchmark.lock` with
 `acquire_lock(lock,45)`. Two Cargo/test workers. Root build target is ONLY
 `.work/fixed-frame-clear-combined-build-01/target`; never clean it.
-Build floor max(14GiB,8GiB+2*allocated shared target); offline analysis12GiB;
 primary14GiB; child8GiB; evidence closure8–10GiB as declared by controller.
-Nushell requires its real six-cache reservation (~47GiB), not26GiB. Use fresh
 admission and safe closed-cache retirement only after preceding guards pass.
-Do not signal/control any peer/user-owned process, terminal, agent or worktree.
 Compiler/Cargo/parser-exporter and application-admission work belongs to peers.
 Root publication worktree `.work/publication-main` was clean at ccb3b465; fetch
 before publishing, preserve concurrent main commits and never force-push.
-No new AWS service/model/subscription/purchase or billing fallback. No browser.
-The saved goal remains paused. Continue manually without goal tools.

Completed exact public cache retirements are closed. Never repeat them: old
scratch/scalar Nushell custom, current-composition token/folded custom+native,
and current-composition Nushell custom. The old repository-parser attempt found
zero eligible files. Preserve all binaries, tools, RBC/catalogs, raw evidence,
private caches, shared target and peer work. Current Nu native/check caches were
not retired and need a new exact ownership/protection audit if cleanup is needed.

The user-owned untracked `suggestions.txt` was re-read and remains SHA256
`4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f`.
[Item-by-item dispositions](docs/SUGGESTIONS-REVIEW-20260913-1245.md).
This remains a selected-function/test-body engine; full libtest, unwinding,
threads and broad OS/FFI support are incomplete. Do not imply full application
coverage or transfer one workload's speedup to all Rust projects.
[Previous detailed state](docs/history/STATE-20260918-before-cold-tail-primary.md).
