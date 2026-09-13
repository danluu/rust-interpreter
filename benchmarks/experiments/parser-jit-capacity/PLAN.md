# Bounded capacity comparison before a lazy-region JIT

The complete parser baseline loses to native by 23.03% on matched-incremental
changed-source wall time. A saved-artifact profile attributes 4,547,956 of
4,831,460 interpreted operations to a single 140,615-operation function. The
actual emitter produces 16,554,488 unprofiled bytes for that function; the
16 MiB arena cannot hold it together with its callers. This is a measured code
capacity issue, not a branch-encoding failure. No names or project identities
may influence runtime behavior.

First implement an explicit bounded code-limit option, keeping the default
16 MiB. Support up to 32 MiB, expose the bound through the VM library/CLI, and
forward an explicitly requested limit through the strict Cargo launcher.
Reject invalid/oversized arguments before guest execution (before Cargo in the
launcher). Preserve zero-capacity interpreter fallback. Do not alter type/borrow
checking, instruction/allocation limits, arena tagging, function caching,
entry/continuation validation or executable-memory publication discipline.
The native entry table keeps its independent bound. All direct branches remain
within the already supported AArch64 displacement range; verify the actual
published code and complete original outcomes rather than relying only on that
range argument.

Qualify default/zero/bounded/oversized CLI cases, both Rust test profiles, strict
fixture/cache/source errors, and every original parser test. Compare saved
default-mode operation profiles/code to the qualified 16 MiB VM where exact
logical inputs permit it. Diagnostic profiler code is larger; do not assume a
32 MiB profiled owner has the same admission outcome as its unprofiled owner.
Preserve every decline or failed assertion in either mode.

The initial changed-source screen uses the complete 114-test gram_core target,
matched `CARGO_INCREMENTAL=1`, two Cargo workers, native default libtest threads
and two custom prepared workers. Freeze a 32-command schedule: native, custom
16 MiB A, identical custom16 MiB B and custom32 MiB, each running original,
wrong initial-lookahead, five cumulative production edits and final restoration.
Use the same new immutable tool for both capacity values and separate Cargo
namespaces. Only the five valid edited states supply paired timing comparisons.
Require unchanged assertions, exact native/custom wrong outcomes, within-state
A/B/candidate artifact identity and complete source restoration. Exclude
unchanged builds, cold controls and wrong edits from the timing ratios.

Predeclare the acceptance rule with the screen implementation, before execution:
the capacity treatment must exceed the observed same-session 16/16 wall envelope
and satisfy its CPU/memory regression bound. A screen may justify a fresh full
three-cycle comparison; it is not an adoption result. Do not retime a failed
unchanged candidate. Report native ratios as well as ratios against custom16.
Do not transfer earlier timings across the combined main exporter/launcher.

The frozen implementation uses median paired32/16 wall plus the maximum
absolute per-edit median16B/16A deviation <1. For CPU the corresponding sum must
be <=1.03. The screen has one observation per edit, so its per-edit median is
that observation. The full study has three. These are observed noise envelopes,
not confidence intervals. Only a passing screen allows a fresh88-command,
three-cycle parser comparison; do not reuse its timing observations in that
comparison. Generated code is bounded32 MiB per owner and guest memory remains
64 MiB with150k live allocations; host peak RSS is not measured by these bounds.
Every successful32 MiB parser command must actually publish over16 MiB. Save all
decline counts. Exact artifacts are compared within each cycle/state across all
three custom arms, allowing already diagnosed rustc allocation-history changes
between cold and restored original states without normalizing any bytes.

Initial admission is24 GiB: four fresh Cargo histories versus the earlier
three-history parser admission of18 GiB. Every command rechecks8 GiB. The driver
records immutable tools, source/assertion fingerprints, command order, artifacts,
native executables, child-tree CPU and complete-command wall time. Artifact
copying and report validation happen outside timing. The two explicit16 MiB
arms pay the same new VM-capability probe as explicit32 MiB. Native and all custom
arms use matched CARGO_INCREMENTAL=1 and otherwise retain repository profiles.
Valid edits rotate through a four-treatment Williams order (A B D C; B C A D;
C D B A; D A C B), continuing across cycles. Each mode occupies each position
equally over four edits, with at most one extra observation per position in the
five-edit screen or15-edit full study. The older three-mode helper is unsuitable
for this four-arm comparison. Original/wrong/restored controls have separately
recorded orders and supply no timing ratios.

The first screen stopped after five controls, before any valid edited timing:
its validator expected runtime counters on a failed test. Failed-test receipts
omit those counters. The original failure and commands remain sealed. A separate
audit verifies the four original commands and first wrong-source custom32
command, exact artifacts, source restoration and frozen code before repair.
The continuation accepts only that exact five-command prefix, retains its Cargo
histories and completes the remaining27 commands under the original schedule and
thresholds. It validates the pending wrong outcomes against native. Counters
are required and bounded on every successful test; unavailable failed-test
counters remain explicitly unavailable. No successful controls are repeated.

Separately count the reached fraction of this function from the saved profile
and inspect its frame/register initialization requirements. If full-function
compilation is too expensive or mostly unused, design reached-region compilation
with cached bounded analyses, atomic publication, fixed assertion identities,
correct successor fallbacks, profile accounting and post-execution code-map
reconstruction. Recomputing whole-function analyses at every newly reached PC
would defeat the purpose. Keep this larger change conditional on evidence from
the simple capacity comparison; no broad memory-model rewrite is authorized by
operation counts alone.

Continue the shared lock, 45-second admission, conservative recorded disk
estimates and 8 GiB command floor. No other-session process control, subagents,
goal activation or AWS purchases. Publish qualified compatibility work separately
from this prospective performance experiment.
