# Public interface edits as the next development-workflow check

The native-call experiment has broader execution qualification, but its original
performance pairs use five small cumulative body rewrites. That cannot establish
how the engine handles changed generic interfaces. Before another runtime tweak,
characterize two actual API generalizations using the same original assertions:

- pgrust `hashfn::hash_bytes(&[u8])` becomes generic over a borrowed
  `AsRef<[u8]> + ?Sized` input. Existing array and slice callers can instantiate
  different call layouts. Run all four original hashfn tests.
- Nushell `Type::list(Type)` becomes generic over `Into<Type>`. Run all fourteen
  existing type-relation tests, including constructor/covariance/OneOf cases.

The two JSON specifications pin the projects and exact single-occurrence source
replacements. They are benchmark mutations of owned snapshots, not patches to
upstream APIs. Each restores the original source. Tests and expected results
must remain byte-identical; the existing wrong-production-edit controls remain.
These are public-interface edits within a selected package. They do not claim
coverage of dependency-manifest, multi-file, macro or downstream-consumer edits.

Extend the tracked workflow harness with a validated public case-file option.
The prior held-out corpus is terminal but incomplete after ENOSPC; its six
completed cases and partial last case are preserved separately. Keep old
cases and commands unchanged. Validate path containment, source pin, field
types, unique tests, replacement counts and selection indices. Freeze the case
file and preserve its hash in each report. Refuse Python -O and unsafe path or
malformed case input before mutation. Reuse the original source-state generator,
negative controls, source restoration, tool identity and artifact verification.

Qualification first: one cycle per new case, original native/Cargo-check/JIT
controls, then verify actual source and artifact receipts. A compile or runtime
failure remains evidence; do not weaken tests to accommodate the interface.
Only after both work, measure **15 cycles of each single edit**, balancing the
three modes through each position five times. Each cycle includes the actual
API edit, an original-source anchor and the existing wrong edit. Fifteen pairs
of the same edit estimate a different scope from five distinct edits repeated
three times; report the two designs separately.

Use original b2 baseline and the fixed resumable/persistent `78e60cdd` candidate,
native root O0/incremental with 18 jobs/default libtest concurrency, custom four
jobs and independent checks. Use matching guest MIR/inlining options within
each pair and record them. No selected Rust/JIT source change is part of this
characterization. Preserve cache-history/artifact differences, all wall/CPU
samples, frontend/lowering/VM stages, and setup exclusions. Do not filter host
contention or control other work.

The outcome is coverage and latency evidence for real interface changes, not
an additional chance to pass the old token cutoff. Both original primary gate
failures remain recorded, and the JIT option remains experimental. The resulting
stage costs and any compatibility failure will choose the next implementation
direction, including whether shared test export/preparation or deeper runtime
work has material end-to-end scope. Full libtest/unwinding/OS/FFI/thread support
and cross-crate invalidation remain separate unfinished requirements.

Status: the harness and independent snapshot verifier now support `--case-file`.
Two specifications pass input checks and 25 malformed/tampered case rejections;
135 synthetic receipt rows validate the fifteen-cycle rotation. Ten IO-failure
checks pass, with actual children drained before restoration. Historical bulk
primary receipts still verify. The [first pgrust interface qualification](../../../results/interface-pgrust-qualification-01/assessment.md)
now passes nine primary commands, three checks and six matching paired artifacts.
The [Nushell qualification](../../../results/interface-nushell-qualification-01/assessment.md)
also passes nine primary commands, three checks and six matching paired artifacts.
Both preserve every original assertion and the wrong-edit controls. The
[pgrust](../../../results/interface-pgrust-repeated-01/assessment.md) and
[Nushell](../../../results/interface-nushell-repeated-01/assessment.md) fifteen-cycle
comparisons are complete: 360 commands/30 pairs/180 artifacts. Keep the two
single qualification pairs separate. Paired artifacts always match; Nushell's
original/wrong-edit artifacts change after cycle zero and remain unresolved.
The small paired changes (−1.14% pgrust, +1.12% Nushell) do not establish a
material benefit from native calls. Nushell's Cargo stage dominates its guest
execution time; the next instrumented cycle attributes those compiler units.

The pgrust qualification, fresh retry of the missing original Nushell held-out
workflow, and Nushell interface qualification are complete. The failed attempt
remains preserved; no partial commands were spliced into the retry or gates waived.
