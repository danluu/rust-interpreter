# Current state — September18,2026

Continue manual optimization indefinitely. Saved goal stays PAUSED. No goal
calls, subagents or independent model calls. Root owns /Users/danluu/dev/rust-interp.
Private repository danluu/rust-interpreter. Preserve all peer work/processes.
Push qualified work regularly; do not stop at milestones.

## Current model

Branch experiment/cross-program-template-model-20260918. Adopted Rust/Cargo
restored exactly atcc4e767a. Current runtime changes are cfg(test) only: the
template/relocation model and saved-artifact replay plus scalar-entry accessors.
No production runtime option/store/persistence/guest execution/native publication.

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

Model02 ated624307 passes12controls/profile under15329/15332, CLOSED21816/21858.
Commitfe4dc9e3 pushed. Explicit scalar/assertion relocation ledger records exact
callee/caller PC or assertion index. Complete ordered sites, encodings, targets,
BLR, same widths, budgets and fresh assertion strings are checked. Every restored
word/metadata matches fresh staging. Other changed immediates remain key misses.

Replay01 at053c7425 passes one explicit ignored release diagnostic under82090/
82093, CLOSED97242/97246. Pushed1f8c1829. Seven actual parser artifacts compared
with original selected2391/1154 active functions. All original templates captured
within32632316/16974468bytes. Valid edits restore1221–1512/601–817 exact templates;
remaining keys miss, no matching key fails restoration. Current scalar proof
tables use synthetic addresses/ascending callee order, not actual runtime arena
or admission order; no execution or production hit-rate claim. Matching IDs
associate with27.4–38.8/18.6–31.1ms original ordinary emission. Single test-mode
key intervals about9.2–9.6/5.4–5.6ms; not end-to-end savings. Docs:
docs/CROSS-PROGRAM-TEMPLATES-20260918.md. All input/output/source hashes closed.

Populated history added at153e3057:64MiB charge, at most16384 entries, two
ordered maps with one recency entry/template. Model03 admission33104/33146 timed
out before any plan/build/test, preserved/closed at6a9a82d8. Model04 at0be791ba
passes14controls/profile under47496/47500, CLOSED63293/63296. History01 atbd00c8fe
passes70734/70737, CLOSED85095/85098. Valid edit1–5 hits worker0:
1512,2389,2389,1221,2000 of2391; worker1:817,1152,1152,601,973 of1154.
Worker0 evicts447/479/635 atedit4/edit5/restored source; worker1 never evicts,
ends2230 variants/40978712chargedbytes. No capture/emission/restore declines.
These remain fixed original numeric function sets and synthetic scalar tables,
not actual later reachability or production hit rates.

Bound Request/Emission API atfe057ce0 computes one identity and immutably borrows
the exact owner/function/options through lookup/restore/capture. Model05 passes
16controls/profile under33836/33839, CLOSED53467/53470. History02 at7102b85d passes
65170/65173, CLOSED69566/69569. All16 worker/state rows match History01 outcomes,
insert/eviction, words and charge; timings intentionally excluded. Single diagnostic
lookup/restore intervals~1.1–2.9ms/0.6–1.6ms perworker on valid edits, not E2E savings.

Native fixtures added at9f573284. Model06 under97392/97395 passed16debug controls,
failed2newnative fixtures: invalid null address0 read, including fresh-JITcontrol.
Release unstarted; CLOSED16247/16250, commit952d23de. Corrected address8 and added
interpreter oracle at504d0d76. Model07 passes18controls/profile under26529/26532,
CLOSED33109/33112, committed3a813d41. Actual distinct scalar addresses, current
callee/data outputs, instruction budgets0–20, frame1–3,memory128/4096, assertion
failure and repeated fresh guest state match freshJIT; successful values/counts
also match interpreter. These2controls deliberately publish/execute nativecode;
all earlier staged models/replays publish none. No original projectguest rerun.

Lazy context integrated at8cae5e11, still cfg(test)-only and absent bydefault.
Jit.prepare_function prepares current scalar callees first, then optional Context
uses the bound Request to restore or freshly emit/capture. Existing normal
finish_preparation publishes it. Context validates the current Program once and
shares a thread-local Rc/RefCell History. Two new controls exercise real lazy
preparation across Programs and storage-decline fallback. Model08 passes20/profile
under59303/59306, CLOSED66549/66552. Commit6aeaef0e adds workspace controller.

ACTIVE at this state update: workspace01 source6aeaef0e, supervisor81196/child81199.
Controller benchmarks/experiments/cross-program-template-model/workspace.py.
Debug passed628tests/15ignored; release still running as last inspected. Inspect
.work/experiments/cross-program-template-workspace-01/status.json and raw records
before any continuation. Freeze Rust/controllers until completed and closed via
workspace.py --close. Never repeat successful debug because later stages fail.

NEXT after workspace closure: actual saved project suites using the lazy cache
context across artifact edits, two owning worker threads with bounded per-thread
histories and normal dynamic suite scheduling. Add opt-in diagnostic verification
that emits fresh staging for each hit and compares exact code/metadata BEFORE
publication, counting verified hits. This is correctness/actual-reachability
qualification, not an end-to-end speedup (verification deliberately re-emits).
Use exact per-state EntryCatalog/hash/outcome bindings from closed real edit
histories, preserve wrong-result edit and restored-source state. No arbitrary
old numeric function-set approximation. Qualify new diagnostic controls before
original-project guest execution. No persistent native files/IPC/CLI/runtime
adoption yet. Saved goal stays paused.

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

Main publication worktree .work/publication-main is clean atcd5ce92a, confirmed
PUSHEDmain, preserving peercd19ee2e (and earlier296a927d/bd7e74a7). Published closed template/history/native-model throughModel07
docs/results/plan only, no runtime candidate; earlier census also published.
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
- Last free about22.7GiB, fluctuating. Parser primary24GiB reservation completed;
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
