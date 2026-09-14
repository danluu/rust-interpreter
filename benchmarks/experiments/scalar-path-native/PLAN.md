# Qualify emitted path guards before production selection

Implement the two-phase contract in scalar-path-guards/NATIVE-PLAN.md. The emitter
uses the original register assignment, stable unique per-node guard value slots,
active checked write ranges and phase-specific phi transfers. Commit contains no
branch to the private-decline handler. A commit Trap/injected invariant returns
status2; guarded Call entries restore their parent ABI and return a distinct VM
error for every status >=2. Only status1 may replay the original Call.

Native selection is test-only through thread-local RAII. Ordinary production
selection remains the parked store-log source. Add eleven controls beside the
ten qualified path-model controls and 22 prior scalar Call references. Native
comparisons run both persistent-register settings and compare full success/error
memory, values, errors, exact counts and per-PC profiles to the ordinary interpreter.
They cover widths, aliases, late faults, full-width values/phis, captured inputs,
resource/budget tails and bounded fallback. Inject a post-store status2 to prove
the increment occurs once and no ordinary Call replay follows.

Run scalar-path-native-01 with43 controls per debug/release profile under the
shared lock, ROOT target, two Cargo workers/test threads, conservative
max(14 GiB,8 GiB+twice allocated target) admission and8 GiB child floor. Freeze
sources and close success or failure. No original-project execution or timing.
Full workspace/Python/strict checks and original workload profiles must follow
before a candidate installation or changed-source primary. Main is unchanged.

Native-01 passes all43 controls per profile, including post-store status2 injection.
Before installation, omit only alias comparisons proved unnecessary by the complete
CFG earlier-write sets (existing32-diamond oracle) or exact low-word affine identity
with disjoint modular offsets (existing wrap/narrowing controls). Every actual
memory range remains checked. Add a heap-free ABI/padding boundary control.
Native-02 runs44 controls per profile plus14 entry/order controls in release.
The shared write-order helper is unchanged algorithmically and remains bounded.
