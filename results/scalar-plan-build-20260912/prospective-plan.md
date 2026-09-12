# General build-time optimization: reuse the certified scalar frame plan

Fixed before candidate timings. Baseline compiler source30404bf; exact installed
compiler/wrapper/VM and instrumentation hashes will be frozen before runs.
The candidate reuses scalar_frame::pack's chosen certified slots, original local
shapes and local extent during aggregate capture, eliminating a repeated scalar
MIR use walk and planner invocation. It preserves independent coloring checks,
exact slot/count/extent checks, all work bounds/fallbacks, aggregate events and
relocation certificates. No persistent cache or Lower::new shape reuse yet.

Measure build-to-ready wall and launcher+waited-child-tree CPU from launcher
main entry until immediately before VM execution, after selected sidecar and
optional trace/call-report checks and stats artifact hashing. Keep Cargo-only
wall/child CPU separately. The SAME instrumented launcher and frozen VM/options
run both arms, and every original assertion still runs. Do not infer build time
by subtracting separate execution timings or treat saved artifacts as builds.
Host tool build and std-MIR provisioning are outside edit timers.

First establish common instrumentation correctness/transparency and an A/A
history with identical tools/options in distinct cache namespaces on public
fre token-phrase-allocation and pgrust default. Use five existing cumulative
production edits, original anchor, negative production edit that compiles but
fails the original runtime assertion, and explicit restored-original build and
execution AFTER SourceEdit's restoration. One batch per command; fixed identical
jobs18, native repository profile and single native test thread. Both custom
arms use JIT resumable calls and persistent registers, std-MIR, strict Rust
checking, unavailable-call traps and normal-return callbacks as the existing
qualified token workflow requires. Fix exact invocation/selection before runs.
All paths use new task-owned public source copies at corpus.json pins, shared
serially by both arms with independent targets. No private holdouts are read.

A/A is diagnostic rather than an optimization result. Require all timing fields,
controls/artifacts and restored states correct. Record descriptive paired wall
and CPU noise; no favorable samples may be selected. If observation is too noisy
for a5%screen, investigate external contention or expand the prospective
measurement before candidate timing, never rerun unchanged failures for a pass.

Candidate first screen uses the same two workloads and five edited pairs each.
Require >=5% median PAIRED build-to-ready wall gain on token, improving median
paired build CPU, and no >5% wall/CPU regression on pgrust. Exclude cold/anchor,
wrong-edit, restoration and optional no-op controls from edit medians. Preserve
all outputs, assertions and bytecode identity; investigate any bytecode drift
before interpreting performance. Both arms have same compiler checking policy,
wrapper/options and VM. No runtime performance claim from this build experiment.

If passing, repeat three separately initialized/order-rotated histories and
public Ruff/Nushell generic-interface confirmation. Require aggregated primary
>=5% gain with improving CPU and each history/confirmation within5% wall/CPU
regression guards. All debug/release workspace tests and focused certificate
and metrics/control tests must pass before merging. Quantify allocator/artifact
tradeoffs as necessary; reject correctness/invalidation problems regardless of
speed. Do not claim cold speedups without a separate fresh-target protocol or
unknown-holdout gains. Do not add nested stage times.

Use original shared benchmark.lock for all builds/tests/benchmarks. No signals,
changes to user-owned source/worktrees/caches, AWS activation or cache purges.
Host free disk is about4GiB at setup; copy bounded public sources and only112MB
of immutable std-MIR metadata, reuse our own host build target, and check at
least1GiB free before starting measured commands. Stop safely on space failure.


Pre-timing baseline update: a fresh origin fetch revealed145new upstream commits
ending at c1c3b3a, including compiler payload diagnostics/reuse and suite features.
No A/A or candidate timings had run. Merge currentmain before both measurements
and adapt the candidate/common metrics/harness to it. The preliminary30404bf
baseline install is retained as unmeasured setup evidence and is not a comparator.
The same5%build gate remains. Current function reuse is opt-in and disabled by
the normal launcher, so both arms lower functions normally. Source pins unchanged.

Exact shared guest configuration for forthcoming fixed public cases: --batch,
--std-mir, --inline-leaves and --baseline-inline-leaves, --guest-mir-opt-level3,
--guest-mir-inline-scale8, --build-tool-opt-level0, --trap-unsupported-calls,
--run-try-callbacks, --instruction-limit100000000000, --allocation-limit150000,
--comparison-engine jit, both-arm resumable calls and persistent registers.
Jobs18 for native/baseline/candidate; native repository profile,1test thread.
Use --expect-identical-bytecode --check-floor --build-metrics --verify-restoration
and --aa-control only for the same-key A/A diagnostic, with --lock-wait-seconds300.

Prospective screen expansion after A/A, before any candidate timing:
Token identical-tools A/A has median paired build-wall change +2.871% with
individual pair range -6.439%..+6.020%, and median CPU +1.714%; pgrust wall
median -0.342% (range -4.059%..+3.496%), CPU median -0.475%. Preserve both
complete histories without subtracting these values from candidate results.
Expand the first candidate screen to THREE independent one-cycle histories on
EACH public workload, initialized in orders native/baseline/candidate,
baseline/candidate/native, candidate/native/baseline. Run every planned history
unless correctness/artifact/space controls fail; no early favorable stopping.
Use all15 edited pairs per project. Require aggregate token median paired wall
gain >=5% with improving aggregate paired CPU, and every individual token
history plus aggregate/individual pgrust history within5% wall/CPU regression.
These three histories replace the original one-history screen plus subsequent
three-history repeat. A passing screen still needs the planned independent
public Ruff/Nushell generic-interface confirmations with5% regression guards.
No candidate tools have been built or timed at this plan update.
