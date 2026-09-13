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
