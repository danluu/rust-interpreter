# Combining session preparation gains with guest execution changes

This experimental composition passed correctness qualification and its initial
changed-source fre screen. Main keeps the adopted scratch/scalar runtime while
the longer project and parser guards remain outstanding.

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

[Parser replay](../results/session-runtime-composition-parser-replay-01/summary.json)
passes1824 original invocations with19815 independently regenerated hits.
[Fre replay](../results/session-runtime-composition-fre-replay-01/summary.json)
passes192 invocations with14548 verified hits. Both preserve original failures,
resource limits, bounded storage and full server CPU accounting and are closed.
The exact normal binaries are installed as experimental tool3ebea1cd.

The independently closed [40-command fre primary](../results/session-runtime-composition-screen-token-01/summary.json)
passes: candidate/adopted wall ratio0.9537077504 plus the maximum individual A/A
allowance0.0373937777 gives0.9911015281. CPU ratio0.9303316367 plus A/A0.0284700056
gives0.9588016423. Candidate/native wall remains1.5416394568, CPU1.9224508795.
All original12 outcomes and the two strict unreachable type/borrow controls pass.

The full176-command, three-cycle fre history is running after
[22 controller controls](../results/session-runtime-composition-guard-protocol-01/summary.json),
including10 freshly executed and12 exact unchanged accounting controls. It uses
eight arms, including the identical runtime with history disabled, native builds,
and Cargo check. Full kernel CPU and session startup/shutdown are charged.
A primary pass admits these guards; it does not establish adoption. Later project
and both parser gates remain required. No timing retries or main runtime adoption
follow a failed gate. Experimental sources remain on
`experiment/session-runtime-composition-20260919`.
