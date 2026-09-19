# Current state — September18,2026

Manual optimization continues indefinitely; the saved goal remains paused.
Root owns `/Users/danluu/dev/rust-interp` on
`experiment/shared-cold-tails-20260918`. No subagents or independent model calls.
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

Next: a bounded saved-code census of host-frame metadata loads/stores in the
adopted native Call/Return paths. Identify exact pairs and sampled instruction
coverage before considering any production change. No guest/build/timing is
admitted by this hypothesis. Avoid duplicating parked cached-continuation or
counter proposals. [Primary decision](results/shared-cold-tail-screen-token-01/ASSESSMENT.md).

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
 Root publication worktree `.work/publication-main` was clean at1dec3a58; fetch
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
