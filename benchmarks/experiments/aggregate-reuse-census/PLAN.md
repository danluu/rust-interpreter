# Next diagnostic: additional private aggregate reuse

The persistent-register candidate (`d664bce` / `e89de7f8`) improves real token
commands 23.6% paired and folded 4.2% against `b2aa6efe`. Token passes its original
gate; folded misses 10%. Fresh folded samples show 24.9% VM frame reservation
and 9.0% generated zeroing, versus 3.6% direct register-array stores. Token has
4.2% VM reservation and 12.8% generated zeroing. These sampled shares guide the
question; they are not estimates of removable time.

Measure whether **additional fully overwritten private aggregate ranges can
share storage across noninterfering lifetimes**. Keep the production layout
unchanged until this scope and the byte-initialization argument are credible.
This is separate from the already parked unused-local and argument-only-zeroing
censuses. Do not count existing scalar coloring or inline-bank reuse again.

## Bounded observer

1. Copy the current exporter into a recorded isolated diagnostic checkout.
   Reuse the installed `e89de7f8` VM exactly. Inject an observer alongside
   `scalar_frame::pack`, where the actual monomorphized MIR/types/layouts and
   the existing coloring model are available. Never select by project or name.
2. Preserve the current primitive eligibility and compare an additional narrow
   class: non-ABI fixed arrays of primitive elements whose complete assignments
   overwrite every byte. Exclude padding, enums/unions and uncertain layouts;
   report them separately. Use exact layout sizes/alignments, with bounded type
   traversal. An aggregate's size alone does not prove a complete overwrite.
3. Record complete writes separately from projected/partial writes. Partial
   writes keep the previous whole range live; they cannot kill all incoming
   bytes. Track index-register reads. Reject address-taking/escaping storage,
   indirect observations, unsupported contexts and call destinations in this
   first scope. Keep ABI locations and every entry-zero read dedicated.
4. Use the actual full-CFG liveness/interference planner, including dead writes,
   simultaneous reads/writes, joins and loops. Retain its resource bounds and
   independent coloring certificate. Compute a hypothetical plan only; do not
   replace `lower.locals`, emit initializers or change frame size/bytecode.
5. Report old/new hypothetical physical extent, additional arrays, excluded
   bytes/reasons, bounds declines and analysis time. Preserve compiler instance
   identity and unambiguous profile joins; display names can collide. Weight
   additional frame-byte differences by exact observed direct calls from the
   matching artifact/profile. Keep unobserved/ambiguous functions separate.

## Qualification and decision

Check the event model against partial stores, initial-zero reads, dead writes,
loop-carried values, address-taking and joins. Use independent small byte-state
examples to show why disjoint named values can still interfere through padding.
Run existing exporter tests in the copied diagnostic build.

Freshly export the original folded/token test selections with their original
MIR settings; require exact bytecode identity to their saved artifacts and the
exact installed VM hash, then run unchanged assertions. Instrumented compilation
times are diagnostics, not speed measurements. Serialize under the benchmark
lock; preserve source ownership, failed attempts and all raw evidence.

Proceed to an opt-in compiler transformation only if it has substantial
additional weighted scope and a complete initialization/escape argument. Frame
layout changes need their own changed-artifact comparison and native correctness
references; do not weaken the current identical-artifact runtime benchmark.
The original b2 targets, held-out regression checks and broader qualification
remain requirements. If narrow private arrays have little scope, explicitly
park them and assess broader lifetime proofs or interruptible native Calls from
the measured costs rather than repeating small copy/zero opcode tweaks.

[E2E result](../../../results/persistent-e2e-01/assessment.md) ·
[Folded sample](../../../results/persistent-folded-sample-01/assessment.md) ·
[Token sample](../../../results/persistent-token-sample-01/assessment.md) ·
[Initialization/alias constraints](../bounded-native-calls/FRAME-REUSE-REVIEW.md)
