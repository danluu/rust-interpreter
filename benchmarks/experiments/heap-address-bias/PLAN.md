# Hoist the heap address bias

Start from main ab6adbe8, preserving its runtime/compiler changes. Neither
failed bridge is enabled or carried into this branch. The original strict
exporter and wrapper remain immutable comparison tools. First establish this
base's compatibility with the retained original artifacts and profiles.

The closed tree-aware sample census finds 125 / 66 self-PC samples in old
heap-offset subtraction/selection and unused read-only selection. These are
6.36% / 4.23% of generated samples in perturbed partial windows, not cycles
or projected latency savings. This supports one bounded address-bias candidate.
Do not repeat the branch-selected or CCMP address checks, budget fusion,
successor flush, indirect transitions, or either failed tree bridge.

At every external native entry, form x7 = heap host base - TAG (wrapping
machine arithmetic) and x8 = TAG + heap length. Keep virtual addresses raw
through their existing complete-range checks; select the host bias and virtual
end with the original unsigned address >= TAG rule. BICS against TAG rejects
exactly raw 0 and TAG for nonempty operations; it does not classify arenas.
Keep the linear read-only limit, heap offset-zero rejection, all high-tag
addresses, zero-byte behavior, fault order, copies, and fallback unchanged.
Only after checks add the host bias. The biased word is not a Rust pointer.
Live backing allocations have length <= isize::MAX, so TAG + heap length
does not overflow. x5/x6 remain the live value cache. Internal native edges
inherit x7/x8; allocating/interpreted operations return before reentry.

Qualify actual emitted fixed and dynamic checks against a separate wide-integer
oracle, including both arena boundaries, high addresses, lengths, counts,
read-only prefixes and preserved registers. Check stable-entry/native ABI,
guarded ranges, ordinary and resumable calls, complete trees, allocation/reentry,
partial-copy faults and exact budgets. Run debug/release workspace controls,
strict/cache controls and original logical profiles before timing. Freeze source
and installed tool identities; record setup time separately. An old profile's
exact native word counts cannot serve as the proof of this mechanism.

Predeclare the existing 40-command changed-source token primary, with paired
wall/CPU and A/A gates unchanged. Only a passing primary admits full token,
folded, pgrust, private rg-aot and Nushell histories under their original gates.
No unchanged rerun or retrospective 8% noise rule. Keep all failed attempts.

Serialize workload/cleanup/diagnostic commands under the benchmark lock with
a 45-second wait and two Cargo workers. Initial build floor 16 GiB, diagnostics 12 GiB,
screen 14 GiB, each child 8 GiB. Retire only exact completed owned compiler
intermediates after source, closure, process, open-file and protected-hash checks;
preserve shared targets, installed tools, snapshots, executables and peer work.

The first focused command builds only the bytecode library test executable in
the already-populated shared target, in debug/release. Give this smaller step
a separate 14 GiB admission, reserving 6 GiB above the child floor; it does not
build exporters, workspace bins or benchmark caches. The existing target uses
2.64 GiB in total. Full tool setup retains its 16 GiB admission. Record this
distinction before starting; no performance gate changes.

After the focused debug/release build passed in 17.12 seconds, replace the
fixed setup floor with the recorded conservative size-based admission described
in QUALIFICATION.md: max(14 GiB, 8 GiB + twice current target allocation), checked
before every compiler child. This reserves more than twice the whole existing
target's contents while retaining the child floor. No new cache/history is
admitted by this setup exception. Build an immutable unchanged ab6adbe8 control
too, so recent main changes cannot be mistaken for a bias improvement.
