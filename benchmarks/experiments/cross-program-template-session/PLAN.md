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

Qualification01 runs full workspace debug/release with feature off/on and builds
the actual release VM with the feature. Expect629 tests/profile without the
feature and633 with it, plus15 ignored in each. This includes21 internal controls
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
