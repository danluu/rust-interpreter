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

The independently closed [full176-command fre history](../results/session-runtime-composition-edit-token-01/summary.json)
also passes. Median candidate/adopted wall0.9414513615 plus per-edit median
A/A0.0268743944 gives0.9683257559. CPU0.9390737150 plus A/A0.0239171867
gives0.9629909017. Candidate/native wall is1.5806520070, CPU1.9441990829.
All original12 outcomes, wrong-source controls, strict rejection and restoration
pass across three cycles. Startup, shutdown and full server kernel CPU are charged.

The identical composed runtime without history has median wall/baseline0.9592759008;
candidate/history-off is0.9773742242. These ratios describe distinct paired
comparisons and are not additive component gains. Pgrust, private rg-aot,
both parser profiles and Nushell remain outstanding. The
[176-command folded guard](../results/session-runtime-composition-edit-folded-01/summary.json)
has now passed and closed: wall/adopted0.9863968592 with A/A0.0197796103,
CPU/adopted0.9649114604 with A/A0.0221465280; regression margins1.0061764695
and0.9870579884 are below1.05. The folded wall difference is within its noise
allowance. Candidate/native wall1.0105716567 and CPU1.0228477609 remain scoped
to this workload. Pgrust is admitted next; no unchanged timing is repeated.
The remaining adapters passed14 parser controls (6 fresh/8 exact reused) and23
fresh large/private controls, both independently closed. Later timing still
requires each preceding gate to pass and close.
A primary pass admits these guards; it does not establish adoption. Later project
and both parser gates remain required. No timing retries or main runtime adoption
follow a failed gate. Experimental sources remain on
`experiment/session-runtime-composition-20260919`.

Pgrust attempt01 stopped before any timed command: the borrow-control fixture
used std in hashfn's no_std crate, causing E0433 rather than E0499. The
[closed failed prefix](../results/session-runtime-composition-edit-pgrust-01/summary.json)
preserves both compiler errors, two normally closed sessions with zero requests,
and restored source. A dedicated controller now uses core in that probe. Its
[closed portable qualification](../results/session-runtime-composition-pgrust-protocol-01/summary.json)
includes four actual pinned-rustc type/borrow rejections across std and no_std,
with no code or metadata emitted. Attempt02 used fresh namespaces and
[passed all176 commands](../results/session-runtime-composition-edit-pgrust-02/summary.json),
including both strict controls. Wall/adopted1.0031383653 with A/A0.0120627776
and CPU/adopted1.0005123570 with A/A0.0131577991 pass the regression margins;
neither establishes a speed improvement. Candidate/native wall1.1193991052
covers the four original hashfn tests. The first audit stopped on source tuples
versus JSON lists with identical contents; a separate auditor normalized that
comparison and independently closed the full history, preserving the first
audit failure. No benchmark command was repeated.
The original controller remains intact. Later parser/large proof bindings are
being requalified to require the corrected pgrust result; no timed samples from
attempt01 exist to reuse or discard.
