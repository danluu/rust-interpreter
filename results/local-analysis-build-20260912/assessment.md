# Local lowering analysis reuse: PARK

The candidate improved median paired token build wall time by **3.629076%**,
missing the fixed **5%** gate. Build CPU improved **4.684199%**. All per-history
and pgrust regression guards passed. Preserve this candidate and its complete
evidence; this screen does not qualify it for adoption or Ruff/Nushell confirmation.

| Complete histories | Edited pairs | Median paired build-wall change | Median paired build-CPU change |
|---|---:|---:|---:|
| fre token 01/02/03 | 15 | -3.629076% | -4.684199% |
| pgrust 01/02/03 | 15 | +0.191102% | +0.296969% |

This distinct compiler candidate combines certified scalar-layout reuse with
initialized local type/shape reuse and pre-planner scalar eligibility reuse.
It preserves normalization and layout validation order, synthetic-lowering
fallbacks, aggregate checking, planner bounds and the independent layout
certificate. Frozen compiler source is `de1df7f3856871d67856a92d7aaf69f566244f6d`;
the baseline remains `c1c3b3a`. The exact source and tool manifests are retained
in [candidate-source.json](evidence/candidate-source.json),
[baseline-source.json](evidence/baseline-source.json), and the tool receipts.

The [prospective plan](prospective-plan.md) fixes three independently initialized
one-cycle histories per project, rotating the initial native/baseline/candidate
order. All 15 edited pairs per project enter the median of candidate/baseline
build-to-ready ratios. The gate requires token wall ratio at most 0.95, improving
token CPU, and wall/CPU ratios at most 1.05 in every history and aggregate pgrust.
No A/A value is subtracted. The [measurement](measurement.json) retains every
ratio, including individual regressions beyond 5%; the guards apply to medians.

Both arms use the same frozen VM and compiler wrapper, published common
instrumentation, strict ordinary checking, separate Cargo caches, JIT resumable
calls and persistent registers, 18 build jobs, guest MIR level 3 and inline scale
8, tool optimization level 0, leaf inlining, std MIR, unsupported-call traps and
try callbacks. Limits are 100 billion instructions and 150,000 allocations.
Native controls use the repository profile, 18 jobs and one test thread.
Persistent function-payload reuse is disabled. All six completed histories retain
their unchanged result directories, 144 primary command records, 48 checking
controls, 96 executed-artifact identities and 30 edited pairs. Original assertions
pass, deliberately wrong production edits compile and fail at runtime assertions,
and each final restored original is freshly rebuilt and executed. Control states
are excluded from the edited medians; corresponding baseline/candidate artifacts
are byte-identical throughout.

The original controller stopped at its 3 GiB admission check after five complete,
verified histories. The sixth history, pgrust 03, had not started. After capacity
increased, the [continuation](evidence/local-analysis-continuation-controller.json)
recorded 4,145,213,440 free bytes and ran exactly the original final benchmark and
verifier commands. It binds the [original controller](evidence/local-analysis-screen-controller.json)
by SHA-256. There is no repeated or partial performance history in this screen.
The 1 GiB per-command floor remained in force, and all planned data is retained.

[Qualification](qualification.json) includes 375 passing Rust tests in each of
debug and release, with one existing ignored test; a 261-input standalone
local-layout oracle; and a successful full validation with 23,727 command
receipts. The latter includes 111 local-layout native outputs, each matched by
both interpreter and JIT. An initial validation adapter run failed to import
`std_mir` after 8,176 commands. Its adapter, traceback, receipts and compressed
command log remain separate from the complete rerun after the adapter added the
scripts import path. The candidate's [full validation summary](evidence/interpreter-validation.json)
is preserved here; the baseline top-level validation report remains unchanged.

An [independent read-only audit](independent-audit.json) recomputed the decision
from raw launch receipts and checked all retained artifact hashes, source
transitions, fresh compilations, command order, isolated caches, common scripts,
frozen tools and qualification counts. [Evidence instructions](evidence.md) and
the [manifest](evidence-manifest.json) map copied files and compressed validation
logs to their original paths and hashes. Executed bytecode, immutable tools and
source snapshots remain under the original task-owned `.work` paths.

These shared-host results describe this build-readiness screen. They do not
establish a runtime, cold-build, whole-command or unknown-holdout speedup.
