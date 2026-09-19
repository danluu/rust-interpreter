# Combining session preparation gains with guest execution changes

This experimental composition has passed correctness qualification; performance
has not yet been measured. Main keeps the adopted scratch/scalar runtime.

Two previous candidates have complementary limitations. Session history and
previous-duration ordering passed the parser gates but failed fre's wall gate.
Native indirect transitions, checked readonly scalar leaves and successor-only
spilling passed all five project histories but narrowly failed the parser CPU
guard. Their measured improvements cannot be added. The combined candidate
requires new tests, real edited-source comparisons and all held-out guards.

The composition exposed a new cache-key dependency: an indirect-call signature
ordinal can change when an unrelated function signature changes. The template
key now binds the exact current ordinal and metadata state. Dynamic layouts,
register-zero requirements and target pointers are read from current owner
tables. Direct-callee, scalar, assertion and literal relocation checks remain.
Session transport explicitly requests and verifies indirect-call options; a
server without support is rejected before an enabled request is sent.

[Full qualification](../results/session-runtime-composition-qualification-02/summary.json)
passes720 Rust tests in each profile, with19 ignored diagnostics, plus446 Python
passes and22 declared skips. Separate diagnostic, scheduler-disabled session,
ordinary-model and default-VM checks pass. The runs account for52 owned servers
and108 clients; independent closure verifies479 inputs and1546 evidence files.
The first workspace attempt stopped at a stale mocked receipt-call expectation;
its failure is retained, and the corrected suite adds enabled-option forwarding.

[Focused interaction controls](../results/session-runtime-composition-focused-01/summary.json)
compare complete guest memory, ordered faults, budgets and fresh layouts across
cached edits. The [primary protocol](../results/session-runtime-composition-screen-protocol-01/summary.json)
has16 controls covering complete session CPU accounting, option isolation,
source transitions and original native outcomes.

Next verify every template hit on saved parser and fre edits, then run one fresh
40-command fre primary with strict unreachable type/borrow rejection controls.
No timing retries or main runtime adoption follow a failed gate. The experimental
sources are retained on `experiment/session-runtime-composition-20260919`.
