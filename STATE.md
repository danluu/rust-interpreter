# Current state — September18,2026

Continue manual optimization indefinitely. Saved goal stays PAUSED; no goal
calls, subagents or independent model calls. Root owns /Users/danluu/dev/rust-interp.
Private repository danluu/rust-interpreter. Preserve other sessions and publish
qualified work regularly. Do not stop at milestones.

## Current direction

Branch experiment/cross-edit-emission-census-20260918. HEADcef2214e before this
state update. Adopted Rust/Cargo was restored exactly at4d06c3ed after parking the
register-workspace candidate. Current Rust difference is a cfg(test)-only
structural census, with no JIT construction, guest execution or native cache.

Cross-edit model01 at91562be3 passes seven debug and release controls under
17320/17323. Source/model inputs remain unchanged. Closer36881/36961 passed.
Controllers are benchmarks/experiments/cross-edit-emission-census.
Observe.py reads eight already-retained parser artifacts
(original, wrong, five valid edits, restored) and emits all seven consecutive
structural comparisons. It requires the closed model and complete parser history.
Observer01 at774fc3dc failed preflight under48617/48620 before any diagnostic:
restored source does not imply identical artifact bytes. CLOSED63286/63337,
with both retained artifacts/source verified. Census02 corrects that extra
assumption, retaining the complete eight-state sequence and per-state arm match.
It invokes one release ignored diagnostic, using the
existing root target; no guest or executable publication. Freeze inputs until
closure. Do not rerun a successful command for later bookkeeping failures.

Census02 at1f64c07f completed under70063/70105, CLOSED76725/76829. All eight
artifacts and seven comparisons verify. No guest/code publication. Across the
five valid edits exact bodies cover~30–100% of all ops, closed direct-call graphs
~13–53%; global context differs on three of five edits. Cold functions included.
Next classify exact global/function/op differences and relate overlap to measured
preparation before choosing a cache mechanism. Do not enable reuse from these
counts. [Assessment](docs/CROSS-EDIT-EMISSION-CENSUS-20260918.md).

Model02 at546029a7 adds typed/global difference classification and passes11tests
per profile under13308/13311, CLOSED21995/21998. Differences01 at32e106d2 passed
under27405/27408, CLOSED35904/35946. Into edit1,2,648functions differ only in
immediates; into edit5,2,769. Data/static bytes change. Edit4 changes names at682
IDs and2,395positional direct-call IDs. Immediate changes are not proven pointer
relocations. Both small edits2/3 change one function and no compared globals.

Model03 at0de25c43 passed12controls/profile under89426/89430, CLOSED5273/5277.
It adds direct-callee-layout candidates, original metadata and an original-anchor
observer. Anchors01 atb8e498b1 under22575/22661 failed the64MiB report bound before
publication (diagnostic child22882 returns101); CLOSED42993/42996. No guest ran.
Failure, inputs and successful earlier controls are preserved.

Model04 atcef2214e passed13controls/profile under63343/63346, CLOSED81375/81379.
Anchors02 at294b8321 passed under85935/85938, CLOSED96565/96595; schema2 report
is22,452,178bytes under the unchanged64MiB cap. Each original function's metadata
is stored once, masks remain per-state. All seven original-anchor comparisons
verify. No guest/code publication.

Weight01 ata3923edc passedfourcontrols and the full saved-trace association under
99970/99973. Closer01 timed out on the peer lock, preserved/CLOSED76400/76403;
closer02 CLOSED86457/86460 without repeating successful work. It verifies exact
original artifact/function metadata and the complete unchanged refined trace.
Valid-edit body/layout candidates associate with26.9–38.3ms original ordinary
emission in worker0 and18.1–30.6ms in worker1, versus23.9ms no-entry reducer
work excluded per owner. This is association with one original instrumented
capture, not edited-run measurements or an upper bound for a populated history.
Workers overlap, phases nest; no CPU or predicted savings claim.

Next preserve/push/publish this completed census evidence, then create a separate
test-only cross-program template model from adopted runtime. Require an explicit
bounded identity for all emitter inputs, exact fresh staging equivalence, strict
matching of scalar target/shape and assertion-base state, budget/metadata guards,
and fresh-program assertion references. No unproved address rewriting. No
persistent storage, runtime integration or timing campaign until proof and review.

Do not change frozen Rust/controllers until closure. Current free about22GiB,
with rapid observed depletion; recheck each stage. No cache or performance
candidate is enabled by the diagnostic.

The census hashes complete functions at identical numeric IDs, then checks direct
callees and an iteratively propagated closed direct-call graph. It excludes
unknown indirect callees. Global metadata, initializer bytes, function count and
whole-program heap-use mode are a separate equality check. Seven controls cover
body/layout edits, cycles, transitive invalidation, duplicate names/IDs, global
changes, invalid/partial artifacts and long chains. This is structural overlap
across all functions, including cold functions, not a complete native-cache key,
cache hits, emitted-code equality or measured savings. Real reuse still requires
emitter/tool/target/options identity, scalar admission and budgets, assertion
rebinding, relocations, bounded storage, corruption/concurrency handling and
normal publication checks. Strict frontend type/borrow checks remain mandatory.

## Just completed and parked

Branch experiment/emitter-register-workspace-20260918 is pushed through40dc130e.
Candidate tool78176777e223ad180f5c47c2a2c28f040a806e63979965c46e0f2bee0614b879,
VM5ec0cc0ef6b3f26335f383ea160e26b63290407f3ab7fde9392fe25da84b0297. Exact adopted
exporter/wrapper.615Rusttests/profile13ignored;434Pythonpass22skip;121strict
checks; both original adopted machine-code arenas reconstruct exactly.

Its32-command genuine-edit full-parser primary at16da7dde completed under3736/3739,
CLOSED33627/33631:5,311frozeninputs112evidence. All114tests/outcomes/assertions,
artifact/catalog identities and source restoration match. Wallratio1.058595656,
A/A0.060960002,margin1.119555658 FAIL. CPUratio1.046235056,A/A0.054013185,
margin1.100248241 FAIL. Candidate/nativewall1.352372254. PARKED; larger histories
cancelled; no unchanged retry or adoption. Controls vary, so this is not a precise
causal regression estimate.

Saved15-receipt audit at2d5eda2d passed10controls under49936/49939,
CLOSED55688/55692. Compile sums215.7/217.6/198.0ms and largest worker126.2/127.9/
114.0ms (adopted/duplicate/candidate); constructor45.3/48.1/49.7ms. Intervals
are elapsed, overlap across workers and do not prove command savings.
[Result](docs/EMITTER-REGISTER-WORKSPACE-20260918.md).

Main publication worktree .work/publication-main is clean at390ecf2d, confirmed
PUSHED to main, preserving peer52f86a1d. It contains docs/results only for this
candidate; adopted runtime unchanged. Fetch before the next publication and
preserve peer commits. Full earlier experiment/qualification/diagnostic identities
are in [previous state](docs/history/STATE-20260918-before-cross-edit-emission-census.md).

## Adopted identities

Tool df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62
VM 6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf
Exporter cf4b3499912506b9ebaed30e6f84e250fccba2d343558dd8cccc847e8a0be96d
Wrapper 45bca4f272e994bff2564c8f5ccbd7f0d2e52cd4235a3105b4af5764e8ed7fc5
Source fca687ebac0ea9374a1426addd01169fe707f608.
Proof results/scratch-scalar-main-qualification-01/summary.json:608Rust/profile,
13ignored;121strict;726five-project commands,both88parser guards,114compatibility.
Still a selected-function/test-body engine; full application threading, unwind
and OS support are incomplete. Compiler/Cargo/application-admission work belongs
to peers; preserve their worktrees/processes.

Same-process shared emission templates are PARKED: wall0.999311805+A/A0.044733804
fails. Do not retime this unchanged mechanism. Broad/conditional demand, implicit
zero, selective regions, shared cold tails, readonly/private scalar stores and
other parked candidates are recorded in the previous-state chain. Preserve their
failed gates and existing successful evidence.

## Resource and ownership rules

- Builds/tests/substantial analysis serialize on .work/benchmark.lock with
  acquire_lock(lock,45). Two Cargo and test workers. Root build target only
  .work/fixed-frame-clear-combined-build-01/target; NEVER clean it.
- Build floor max(14GiB,8GiB+2*allocated target); analysis12GiB; closures8GiB.
  Parser primary reserved24GiB and is completed. Future real Nu campaigns need
  their full recorded reservation (~47GiB), not a lowered floor to fit the host.
  Free space was about23GiB before model build; recheck each admission.
- Independent cleaner read-only status:
  /usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status
  Do not repair/restart/compete with it. Never signal or control a peer/session.
- Exact Nu native_lines and native intermediate retirements are closed; do not
  repeat. Nu check attempt01 timed out before admission and is preserved.
  Attempt02 atafa80866 passed under77691/77718, CLOSED87209/87213:2,687files,
  about1.49GiB free recovered,9,647protected hashes unchanged. Keep sources,
  binaries, RBC/catalogs, raw proof, tools, private caches and peer caches.
- No AWS purchase/activation/model/billing fallback; no browser.
- User-owned untracked suggestions.txt is unchanged SHA256
  4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.
  Read again this turn. Dispositions: docs/SUGGESTIONS-REVIEW-20260913-1245.md.
