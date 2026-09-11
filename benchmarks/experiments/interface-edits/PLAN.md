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

First extend the tracked workflow harness with a validated public case-file
option after the current held-out corpus is terminal and evaluated. Keep old
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

Status: specifications prepared; harness integration and actual runs pending.
