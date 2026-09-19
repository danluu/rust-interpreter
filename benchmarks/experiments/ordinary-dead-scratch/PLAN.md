# Scope overwritten native temporaries in ordinary JIT regions

Fresh process counters show current adopted JIT/native instruction ratios of
3.56/5.25 for the original block/exhaustive assertions. Before implementation,
measure a separate scope from the parked scalar-callee dead-register pass:
overwritten pure definitions inside ordinary emitted operation/overhead spans.

Reuse the exact closed scalar-word-census03 finite AArch64 dependency decoder.
Do not extend its encodings. Unknown instructions are full liveness barriers;
all loads, stores, stack adjustments and control transfers stay. Mark every
mapped span boundary and every direct branch target (B/BL, B.cond, CBZ/CBNZ,
TBZ/TBNZ across the complete captured code) as a basic-block boundary. Control
transfers are barriers even when the legacy decoder understands them. Treat all
registers, SP, flags and the modeled vector state as live at every boundary.
Scalar whole-body spans are excluded. No inter-operation, inter-region, loop,
ABI-exit, or speculative reachability proof is inferred.

Run the nine original decoder controls and new boundary/side-effect controls
before reading real code. Count only pure definitions overwritten without a
read in the same bounded segment. Include a seeded independent def/use oracle
on straight-line abstract operations. Revalidate both current adopted captures
and original profile identities with the qualified schema2 map validator.
Join every retained self-PC sample; collapsed samples spanning dead and retained
words stay ambiguous. Static word counts and partial samples are separate;
neither is retired instructions, latency, or a performance adoption result.

No runtime patch, compiler, guest, executable publication, timing, or default
change. The old scalar pass and all rejected direct-operand/width experiments
retain their decisions. Any future emitter treatment requires its own proof,
semantic qualification and existing source-edit primary/all guards.

Shared lock45s; initial12GiB, child/case/closure8GiB. Bound captured code to the
existing16MiB map limit and each analyzed span to65,536 words; larger spans are
explicitly excluded. Freeze all inputs/controllers through terminal and an
independent recomputation. Preserve other sessions and the paused goal.
