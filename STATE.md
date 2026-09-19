# Current state — September18,2026

Continue manual optimization indefinitely. Saved goal stays PAUSED. No goal
calls, subagents or independent model calls. Root owns /Users/danluu/dev/rust-interp.
Private repository danluu/rust-interpreter. Preserve all peer work/processes.
Push qualified work regularly; do not stop at milestones.

## Current model

Branch experiment/cross-program-template-model-20260918, HEADdecd0732 before this
state update. Adopted Rust/Cargo restored exactly atcc4e767a. Current changes are
cfg(test) only: jit/cross_program_templates.rs and one scalar-entry snapshot
accessor. No runtime option/store/persistence/guest execution/native publication.

Model01 atf624e5e7 passes8controls/profile under73219/73339, CLOSED87399/87403.
Source/controllers frozen through completed closure. Controller:
benchmarks/experiments/cross-program-template-model/focus.py. Plan in samefolder.
A checked token validates bytecode structure, rejects partial headers and binds
the exact owner. It supplements, never replaces, existing strict Rust checking.
Identity includes explicit emitter fingerprint/domain, version/target/count,
heap/persistent/scalar/test options, caller ID/full Function, direct-callee layout
and current scalar bytes/step shape/target, assertion base when used. Key stream
cap4MiB; bounded ops/registers/call sites. Trusted in-memory template cap64MiB
retained payload/slack; no allocator-RSS guarantee. Restore checks key, code/table
budgets, entries/resumes/assertion PCs and rebuilds assertions from currentprogram.
Eight controls compare exact fresh words, metadata and counters across distinct
programs, changed initializers/callee bodies, options/layout/identity mismatches,
bounds, scalar targets/step shape, invalid metadata and branches/loops. Arenas
remain absent. No production integration or timing claim.

Next: extend only the test model to record explicit scalar-target and assertion
immediate relocation sites in the emitter (cfg(test)). Rebind only those sites
across owners/programs, checking completeness, original instruction sequences,
new shape/target, same instruction width, budgets and exact fresh staging.
Changed caller immediates still invalidate identity. Width mismatch declines;
no shifting branches or unproved guest-address normalization. Preserve the
strict model controls. Further runtime/storage work requires separate proof,
qualification and genuine-edit timing. No new candidate is adopted.

## Completed cross-edit investigation

Branch experiment/cross-edit-emission-census-20260918 pushed2aca4f1f. All actual
model/observer failures, inputs and successful controls preserved and closed.
Detailed IDs in [previous state](docs/history/STATE-20260918-before-cross-program-template-model.md).
Seven initial structural controls/profile, then11 typed-difference controls,
12 original-identity/layout controls and13 deduplicated-report controls passed.
Original preflight incorrectly assumed restored artifact-byte equality; closed
before comparing the actual distinct artifacts. Anchors01 exceeded64MiB report
bound before publication; closed. Anchors02 stores metadata once and is22,452,178
bytes under unchanged64MiB cap. No guest/JIT/code publication in these analyses.

Saved artifacts show data/static bytes and many immediate values shifting across
edits; edit4 changes names at682IDs and2,395direct-call IDs. Immediate-only does
not mean safe pointer relocation. Edits2/3 change one function, globals stable.
Weight01 ata3923edc passes4controls and complete retained-trace association under
99970/99973, CLOSED86457/86460 after a preserved closure-lock timeout. Original
artifact/function metadata match; no-entry functions excluded. Body/layout
candidates associate with26.9–38.3ms original ordinary emission in worker0 and
18.1–30.6ms in worker1. These overlapping/nested diagnostic intervals are not
CPU, edited-run measurements or predicted savings, nor a populated-cache bound.
[Assessment](docs/CROSS-EDIT-EMISSION-CENSUS-20260918.md).

Main publication worktree .work/publication-main is clean at7e225ae1, confirmed
PUSHEDmain, preserving peer9e63e174. Census docs/results only, no runtimecandidate.
Fetch before future publication and preserve peer commits; never force push.

## Adopted runtime and parked changes

Adopted source fca687ebac0ea9374a1426addd01169fe707f608.
Tool df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62
VM 6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf
Exporter cf4b3499912506b9ebaed30e6f84e250fccba2d343558dd8cccc847e8a0be96d
Wrapper 45bca4f272e994bff2564c8f5ccbd7f0d2e52cd4235a3105b4af5764e8ed7fc5
Proof results/scratch-scalar-main-qualification-01/summary.json:608Rust/profile,
13ignored;121strict;726fiveproject commands,both88parser guards,114compatibility.
Selected-function/test-body engine: full application threading/unwind/OS support
incomplete. Compiler/Cargo/application-admission work belongs to peers.

Emitter register workspace78176777/VM5ec0cc0e passed615Rust/profile,434Python+
22skip,121strict,exactoriginalcode reconstruction, then FAILED32-command parser
primary:wall1.058595656+A/A0.060960002=>1.119555658;CPU1.046235056+
A/A0.054013185=>1.100248241. Candidate/native1.352372254. Parked; larger commands
cancelled; no unchanged retry. Branch pushed40dc130e; result docs onmain.
Same-process shared templates also parked:wall0.999311805+A/A0.044733804fails.
Other parked demand/zero/cold-tail/scalar/composition experiments remain in the
previous-state chain. Do not retime unchanged candidates or reinterpret gates.

## Resource, ownership and recovery

- Builds/tests/substantial analysis: root .work/benchmark.lock,acquire_lock(lock,45),
  two Cargo/test workers. Build target ONLY .work/fixed-frame-clear-combined-build-01/target;
  NEVER clean it. Build floor max(14GiB,8GiB+2*allocated target),analysis12GiB,
  children/closures8GiB unless higher declared. Recheck each stage.
- Last free about24.8GiB, fluctuating. Parser primary24GiB reservation completed;
  future Nushell full comparison needs its recorded~47GiB, not a reduced gate.
- Cleaner read-only: /usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status
  Do not repair/restart/compete with it or signal/control any peer/session.
- Exact closed Nu native_lines/native/check intermediate retirements completed;
  do not repeat. Check02 recovered~1.49GiB,2,687files,9,647protectedhashesunchanged.
  Preserve sources,binaries,RBC/catalogs,raw proof,tools,private/shared/peer caches.
- No AWS activation/purchase/model/billing fallback; no browser.
- User-owned untracked suggestions.txt remains SHA256
  4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.
  Reread this turn. Dispositions docs/SUGGESTIONS-REVIEW-20260913-1245.md.
- Preserve successful commands and captures. Inspect exact receipts after any
  interruption; never infer completion or rerun successful work for bookkeeping.
