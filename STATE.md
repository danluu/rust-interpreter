# Runtime continuation, September19: current composition parked

Continue indefinite manual optimization with genuine changed-source benchmarks.
No final at milestones. No subagents/independent models, goal tools, AWS/browser
work, peer process control or broad cleanup. Saved goal stays PAUSED. Only this
checkout and .work/publication-main are ours; preserve compiler-session ownership.

## Decision and next work

Session/indirect/readonly/spill composition (runtimeb34b6f10, launcherfixd293d909)
passed its40-command primary and four full176-command project guards. Its
110-command incremental parser gate is independently CLOSED40244: correctness
and all114 original tests pass, but wall ratio.9191148450 + maxindividual
A/A.1141285168 =1.0332433618 fails the strict improvement gate. CPU ratio
.8975027572 + A/A.1086873477 =1.0061901048 passes. Verdict UNMEASURABLE.
Repository-default parser and Nushell are CANCELLED/UNSTARTED. No unchanged
retiming, gate change or adoption. Main remains scratch/scalar df4006e0.

Saved parser A/A audit01 is independently CLOSED68081:15pairs/60reports; no
new timings. Largest wall control difference234ms includes226ms in the recorded
build-to-ready interval. All pairs and the original gate are retained; no host
cause is inferred. Candidate parser medians: command1.6260s, build1.2821s,
execution.272664s, longest test.214753s, compile work.052302s, preparation
work.033261s,3609template hits. Separate intervals/work medians are not additive.

Next: fresh normal-VM native-PC diagnostics of current composition on the two
original fre token block/exhaustive tests, prioritizing the longest block test.
Existing samples are from the older duration-only parent, not this composition.
First extend/qualify scripts/sample_owned_vm.py and summarize_owned_sample.py to
accept, record, forward and validate --jit-indirect-calls (requires resumable).
Preserve old summary option shapes when the field is absent; reject an unrecorded
indirect flag. Extend attribution controls and validate CLI rejects bad options
before launching a child. No Rust/runtime implementation change yet.
Then prepare exact frozen artifact/catalog/source/tool identities and same-process
code reconstruction before any new sample. One fresh3s window/test, ordinary
entropy/assertions/limits, exact owned PID/parent/cwd checks; let guest exit normally.
Diagnostic samples are perturbed and must not be used as latency or speedup claims.
Do not repeat old general-address/bias/budget/frame-base/threshold candidates.
Single-digit-ms parser validation does not justify a speculative validation cache.

## Qualified candidate identities

Installed tool3ebea1cdc1a521169df8bba1ca139df97759aaf200798c2bcb91bef4cba3c5ad
Normal VM78378e47c23ea937598285e2e0c4a73a2bd10787e4afa1cf21d9c0189152182a
Server18fba6dc5673d5f0c95291b2535efcd635689194af7813eedca0d0c279f7a408
Retained .work/session-runtime-composition-qualification-02/release-rust-interp-template-session
Server feature jit-session-duration-order;64MiB history/worker,two workers,
16MiB native arena,threshold65536,shared/bufferedkeysOFF,digestON.
Template domain cross-program-staging-literals-v3 binds indirect signature
ordinals, metadata state and spill flag. Dynamic pointers/layouts are current-owner
values. Full Rust checking precedes every guest. Compiler/exporter/wrapper match
adopted df4006e0. Selected test-body engine; not full applications/general threads.

Qualification02 CLOSED61016:720Rust/profile19ignored;446Python passes22skips;
52servers108clients. Failed qualification01 is preserved. Parser verified replay
CLOSED91007:1824invocations/19815hits;fre replay CLOSED12775:192/14548.
Install CLOSED25894. See archived detailed state for all protocol/source bindings.

## Completed performance guards

- Primary40 source15261907 CLOSED84442: wall.9537077504+AA.0373937777=.9911015281;
  CPU margin.9588016423. Nativewall1.5416394568.
- Token176 sourcef43a950e CLOSED35515: wall.9414513615+AA.0268743944=.9683257559;
  CPU margin.9629909017. Nativewall1.5806520070;12 original tests.
- Folded176 source07f614bf CLOSED95676: wallmargin1.0061764695,CPU.9870579884,
  nativewall1.0105716567;18tests. Wall difference inside noise.
- Pgrust02 source34dd8e57 CLOSED4260: wallmargin1.0152011429,CPU1.0136701561,
  nativewall1.1193991052;4tests,neutral. Pgrust01 failed before timings because
  std::hint in no_std; failure CLOSED97727. Portable core probe26controls CLOSED40059.
  Separate pgrust auditor preserves a tuple/list comparison failure without timings.
- Private rg01 sourcef799aa49 CLOSED94315: wallmargin1.0308613865,
  CPU1.0375064256,nativewall.5910980861;one test,two persistent slots fully charged.
  Actual outer run has suffix-admitted-02; raw/result suffix01. Initial lock
  admission with no workload is separately closed; do not overwrite either attempt.
- Parser incremental01 sourceb77d3754,87651/87654 CLOSED40244:110+2strict,
  UNMEASURABLE as above; nativewall1.2528526703. No later guards start.

Four-history cost audit01 CLOSED70818:240reports/four original verdicts reproduced.
Token candidate execution2.2007s, longesttest2.1334s,compile work.1981s;
history-off2.2714s/.2645s;adopted2.4233s/.2592s. Pgrust/rg guest execution
.0179s/.0055s. No additive gains or guest attribution of compiler improvements.
Docs: SESSION-RUNTIME-COMPOSITION-20260919.md, SESSION-RUNTIME-COSTS-20260919.md.

## Storage: completed exact operations, NEVER repeat

Transparent compression01 stopped after132 verified replacements; its next
original remained intact on a creation-time mismatch. Recovery01's disposable
write-open decompressed the fixture/changed mtime. Recovery02 qualified exact
native creation-time copying via READ-ONLY descriptor, CLOSED66894. Continuation02
completed only241 remaining entries, including the preserved pending copy.
All373 original public .rbc hashes/paths/required metadata preserved; allocated
bytes10960859136->3113185280 (7.31GiB less), independently CLOSED52338. Inode/ctime/
compression flags intentionally change. Sources/caches/tools/private/peer data
untouched. Both historical stat inventories and every failed prefix are preserved;
they MUST NOT be rerun as current-inode inventories. See PUBLIC-EVIDENCE-STORAGE-20260919.md.

New folded cache retirement01 source4e85c8fd,81859, CLOSED30514: nine exact
completed folded compiler namespaces,13399nonexecutable intermediates,
3528406775logical bytes;all3750protected hashes unchanged. Actual free rose
23087607808->25243975680 (about2.01GiB). Never repeat. Current parser caches retained.
Primary retirement CLOSED60900 (3191files/2792protected),token CLOSED33463
(13399/3759),old failed-parser CLOSED96652 (14333/11256) are also complete.
Older Nushell native/custom/check caches already retired. No hoped-for repeats.

## Resources and publication

Shared .work/benchmark.lock,45s admission; two Cargo/native/test workers.
Shared .work/fixed-frame-clear-combined-build-01/target MUST NEVER be cleaned.
Build floor max(14GiB,8GiB+2*current allocated shared target), recalculate.
Analysis/replay12GiB;close/children8GiB;fre16GiB;parser24GiB;Nushell66.54872655GiB.
Last free23.5GiB. Memory check before parser:48GiB host,46% free. Recheck.
Cleaner read-only: /usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status.
No competing cleanup/guard, signaling, or peer session manipulation.

Current root branch experiment/session-runtime-composition-20260919; last commit
d71152ec closes parser-variance audit. No commands remain active after68081.
Main last pushedf8253368 preserves peerdfc0b83e and closed storage/four-history
costs. Parser decision/variance/folded-retirement proof publication is pending.
Root remote lastb77d3754. Fetch/ff publication-main, copy exact qualified paths,
never overwrite compiler work or merge experimental runtime. Push root regularly.
Create a new experimental branch for the diagnostic helper changes after committing
this checkpoint. All old qualified source files stay available in Git.

suggestions.txt is unchanged,user-owned/untracked,SHA256
4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.
Full review docs/SUGGESTIONS-REVIEW-20260913-1245.md. Earlier detailed state archived
in docs/history/STATE-20260919-before-parser-noise-audit.md and older archives.
