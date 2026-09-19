# Shared emission templates: staging prototype

The completed preparation audit finds duplicated per-worker native preparation,
while the cross-edit feasibility census shows substantial identity churn for
token. Prototype sharing immutable function templates within one prepared suite
first. Both owners borrow the same fully checked immutable Program. There is
no persistent file cache, cross-program lookup, skipped checking, or shared
executable arena. Each owner keeps fresh guest state and its own MAP_JIT arena.

Stage1 is compiled only under cfg(test). It adds precise emission-site records
for assertion fault immediates and scalar target immediates, captures relative
entries/resume tables plus original assertion PCs, and reconstructs a staging
object for another owner without publishing or executing code. Relocations
must contain the exact canonical existing MOVZ/MOVK sequence; scalar sites must
lead to BLR x16. Re-encoding a value must retain its instruction count or miss.
No branch widening or heuristic scan of arbitrary native words is permitted.

Scope is exact Program address/lifetime, numeric function ID, emitter options
and each direct callee's actual scalar admission/shape. Current scalar target
addresses and per-owner assertion indices are rebound explicitly. Ordinary
callee layouts/zeroing and function bodies are identical by immutable Program
identity. Scalar preparation must still run independently before a future
lookup, preserving proof-work, scalar-work and code-budget accounting. Disabled
tree/stub/profile modes remain disabled. Finite code and resume-table capacity
are checked before restoring; no admission failure changes owner state.

Six focused controls compare every native word, relative entry, resume offset,
assertion message/owner and statistics against fresh emission. Cover multiple
assertions and repeated scalar targets, zero/nonzero assertion offsets,
changed scalar admission, immediate encoding width, distinct Program objects,
different IDs/options, code and resume-table bounds, malformed relocations,
overlap, missing sites and native-word corruption. A template is a trusted
in-memory product of this emitter, not a deserializer for untrusted native code.

No runtime path or CLI option is wired in Stage1. Test-only observations omitted
by restoration are not used to qualify guest execution. Before production
wiring, add bounded storage, thread sharing, accounting, exact owner lifetime,
cache-miss fallback and original-assertion/error/budget execution tests. Then
qualify workspace/strict checks and real changed-source benchmarks, with all
lookup/locking/copying/population costs inside command timing. Parser-focused
gating may be appropriate only after actual sharing coverage is established;
the parser is pgrust gram_core, not Nushell (older internal labels are wrong).

Serial root lock with45second wait; two Cargo/test workers; existing root target
only; build floor max(14GiB,8GiB+2*allocated target),8GiB child floor. Freeze source
before executing focused debug/release tests. Preserve failed attempts and all
successful commands; close original terminal evidence without rerunning them.

Stage1 is closed after6controls/profile. Stage2 adds6store controls (12total):
exact retained-capacity accounting, one-object publication, full-store fallback,
wrong Program and initial bounds, concurrent publishers with independent scalar
addresses/assertion IDs, lock-free restoration after snapshot, snapshot lifetime,
and poisoned-lock fallback. Storage is limited to64MiB including vector capacities
and conservative object/allocation slack. This is a retained-storage accounting
limit, not a promise about allocator RSS. Store/Template are Send+Sync; Jit never
crosses the worker boundary. No guest or production cache wiring is introduced.

Stage2 is closed after12controls/profile. Stage3 adds five controls (17total),
including four explicit native-execution fixtures on this AArch64 macOS host.
The test helper prepares scalar callees, restores/emits, uses the ordinary
finish_preparation publication path, and executes through the unchanged VM.
Each fixture's second owner must actually hit the shared templates; both live
owners' native arenas must differ. Compare successful values/instruction/memory
counts and exact ordinary-JIT errors across all0..22instruction prefixes, memory
and frame limits, assertion/trap/memory failures, repeated fresh static/TLS state
after success and failure, a full template store and zero native arena capacity.
Also reject partial-validation Programs before template capture/storage. This
stage publishes and runs small native fixtures; it runs no original project
benchmark and still introduces no production runtime/cache option.

Stage3 is closed after17controls/profile. Stage4 connects the same staging path
to an explicit --jit-shared-templates prepared-suite option, default off, and a
public PreparedTemplates/PreparedJit::new_with_templates API. One effective suite
worker takes ordinary preparation. Per-owner deltas and retained-store totals
are reported without calling hits/bytes saved time. Scalar preparation remains
before lookup; normal finish_preparation alone publishes. Metadata recording is
disabled for unshared production owners. Two new controls exercise actual lazy
runtime/API hits, exact Program identity, repeated entries, and concurrent native
owners. Run19controls/profile plus a non-test release VM build, freezing and
retaining the executable separately. No original project guest or timing is
admitted in this stage. Full workspace, launcher/protocol, strict rejection and
original workload sharing coverage remain required before benchmark admission.

Focused04 never acquired the lock and started no build/test. Preserve that
admission receipt before changing its controller run ID. The next focused run
must include the bounded-capture control (20Rust/profile),16focused Python tests
from test_isolated_launcher/test_shared_templates, and a retained non-test VM.
Freeze launcher/receipt helper/test sources as well as Rust. Full build01 is
prepared to require a closed focused05, run the workspace in both profiles
(at least635passing tests,14declared ignored, all20template controls named),
and the full Python suite (at least456discovered,22declared skips). Reuse the
exact already-built focused VM if every Rust/script/test binding still matches;
do not rebuild it just to install. Compose only that VM with the adopted
exporter/wrapper, preserving their exact hashes. This full stage remains
unstarted and needs a result closer before execution.
The success closer is now prepared as close_stage.py; it accepts only named
shared-emission-templates focused/build stages, verifies archived source,
captured logs, installed artifacts and the original supervisor terminal. A
partial failure must still be preserved before correction; never rerun a
successful workspace stage solely because later Python/bookkeeping failed.

Focused05 failed controller syntax before admission. Focused06 preserved16
passing Python controls and a Rust compilation failure from an existing test
closure. Focused07 corrects the closure lifetime and passes20Rust controls per
profile, retaining the16Python controls without rerunning them, plus a production
VM build (SHA d071c9123c40cd9ee9ad4dd1bb13faed046373a7d743ebc85919b08c029e8ebd).
It is CLOSED; build01 now requires focused07. The original-suite controller and
its closer are prepared for the13-command contract in QUALIFICATION.md, after
full workspace and121strict commands. No original workload has run yet.
