# Explicit session for cross-command template reuse

The closed model and actual parser edit replay precede this candidate. All1,824
test-body invocations match native expected outcomes and16,301 reused blocks
match fresh emission before publication. This establishes correctness for the
retained states, not an end-to-end speedup. Keep the adopted engine unchanged.

First expose the bounded trusted-memory primitive behind jit-template-session.
TemplateHistory stays on its creating thread, retains no Program/native-arena/
guest ownership, and has no serialized-code loading API. PreparedJit's explicit
constructor validates the current Program once, rejects partial headers, creates
fresh metadata/native owners, and attaches the context. Current scalar proof and
admission still precede template lookup; current capacities and budgets govern
publication. History limits remain512bytes..64MiB, with at most16,384 entries.
Storage charge bounds payload/capacity plus declared map slack, not allocator RSS.

Optional verification compares every staged executable field with fresh emission
and returns a fatal preparation error on mismatch. It is available in feature
builds as a diagnostic; timing must disable it. Ordinary builds contain no history
fields or relocation ledger. Feature builds with no explicit history still use
ordinary emission and are a required mechanism control.

Qualification03 completes full workspace debug/release with feature off/on and builds
the actual release VM with the feature. Expect629 tests/profile without the
feature and633 with it, plus16 ignored in each. This includes21 internal controls
and four public-API integration controls compiled against the non-test library:
changed scalar callees/data and dropped original owners; code/runtime budgets,
mode changes and current failure text; validation/partial-header/storage rejection;
bounded/full/dropped storage fallback. Native fixtures execute deliberately.
No original-project guest command is run at this stage.

Next use an explicitly started local session with two owning workers and bounded
requests. Only trusted templates survive requests; Programs and native owners are
recreated. The launcher still completes strict Rust checking before every request.
Protocol must bind selected artifact/catalog/options, preserve current execution
environment semantics, reserve reports before guests, handle failures without
poisoning subsequent requests, and terminate through its own protocol. No signals
or process manipulation of other sessions. Do not load native cache files.

Qualify transport on fixtures and actual saved suites before timing. The primary
compares complete changed-source commands against adopted fresh-process execution
and ordinary native Rust, with a session-without-history control to expose the
transport effect. Charge startup and all session CPU; never rely solely on the
client's waited-child CPU or hide setup in an unmeasured daemon. Existing primary
admission/noise gates and subsequent project guards apply. No unchanged retry to
seek a pass. Parser primary needs its full24GiB reservation; Nushell about47GiB.

All builds/tests/substantial analyses hold root .work/benchmark.lock with45-second
admission and two Cargo/test workers. Reuse only the existing
.work/fixed-frame-clear-combined-build-01/target and never clean it. Initial build
floor is max(14GiB,8GiB+2*allocated target); recheck before each command, with8GiB
minimum for closure. Preserve every completed command on later failure, freeze
source before execution, and close each attempt before correction. No subagents,
goal-state changes, AWS activation, browser, or control of peer processes.

API01 did not start a controller/build/test: controller generation failed and the
supervisor attempted the missing file. Its terminal is closed and retained. API02
is the first actual qualification; source and intended tests are unchanged.

API02's default debug command passes629 tests with16 ignored. The controller
incorrectly expected15: the new explicit saved-suite diagnostic adds one ignored
test after workspace01. Preserve/close that successful command and its harness
failure. API03 verifies all Rust/Cargo hashes and reuses the completed default
debug command; only the four unstarted commands run. No Rust correction or rerun.


API03 preserves the default debug pass and also passes629 default release tests,
16ignored. Feature debug compilation fails before tests: a model-only constructor
was missing cfg(test), calling another test-only helper. Close this attempt.
API04 changes exactly two cfg annotations (moving a redundant attribute to the
intended helper), verifies that exact source delta and every other Rust/Cargo
hash, then runs the full feature workspace in both profiles and builds both
ordinary/feature release VMs. The default test bodies remain unchanged under
configuration, and their prior completed checks remain cited, not re-executed.

API04 also corrects the as-yet-unexecuted feature-only integration oracle to pass
ordinary interpreter options, rather than JIT flags that its public API rejects.
The controller checks these exact fixture substitutions againstAPI03 source;
no default test is affected. This correction precedes the first fixture run.

API04 is closed:633 feature workspace tests/profile,16ignored, ordinary and
feature release VMs built and retained. Transport01 adds per-request environment
snapshots (no host set_var) and an explicit inherited-pipe session binary. Two
owning threads retain histories while native owners/guest state are recreated.
Requests bind artifact/catalog hashes, current directory, explicit bounded limits
and a new report path; frames are capped at4MiB and sequence/count at4096requests.
There is no socket, daemon auto-start, native-code loading or launcher route yet.

Transport01 runs30 focused controls/profile:5 existing environment controls with
the feature and5 without,3 wire/CPU controls,8 existing PreparedJit controls,
6 history/current-input controls and3 real session-process fixtures. The latter
launch four owned sessions/profile: history off/on execute six changed32-test
fixture suites, rejection recovery executes one suite, and malformed framing
closes its session. All processes exit through the protocol or EOF and are waited
for; no signals. Preserve their files/receipts and both session executables.
No original project guest or source-build benchmark is run in this stage.

The server records process user/system CPU using the installed Darwin SDK's
getrusage ABI; request snapshots exclude response-writing tail CPU. Final kernel
process accounting must reconcile startup/tails/teardown in the later E2E driver.
Error responses conservatively report that execution may have occurred; clients
never automatically retry. A worker/channel failure closes this owned session
after joining its workers; guest assertion failures leave later requests usable.
