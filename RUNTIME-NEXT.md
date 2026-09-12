# Next work

Use [STATUS.md](STATUS.md) for the current measured build and controls and
[the September 11 review](docs/SUGGESTIONS-REVIEW-20260911.md) for individual decisions.
Historical plans and failed gates stay in Git and their linked result directories.

1. **Measure export overhead on the retained compiler.** The scalar ABI screen
   failed: token improved only 0.74% against an 8% target. Guest execution saved
   about 170ms while Cargo added 144ms. Its full A/A and held-outs are stopped.
   Attribute validation, lowering/proofs, serialization, hashing and publication
   before choosing another optimization. Keep exact bytecode identity and strict
   type/borrow/error controls. Tool lookup is about 2ms, not the main bottleneck.
2. **Qualify stronger native controls.** Compare fixed debuginfo and
   split-debuginfo presets, record native build and test execution separately,
   and retain complete-command timing. Use calibration edits to choose a preset
   before held-out edits. The development branch now shares an 18-worker latency
   preset; report CPU costs and preserve explicit settings for old comparisons.
3. **Exercise a real unfiltered suite.** Start with fre-kernels: native all-tests
   timing, exact guest executed/ignored/unsupported inventory, original assertions.
   Direct body coverage is not libtest compatibility. Address real unwinding,
   thread and OS/FFI gaps without success shims. Model an explicit hybrid at
   Cargo-target compilation granularity before implementing one.
4. **Use structural runtime work when measurements justify it.** Preserve the
   scalar source branch for register-allocation work. First count JIT reentries,
   preparation and repeated compilation costs. Audit old trees/stubs before
   consolidating around resumable calls and persistent registers. Add seeded
   valid-program differential testing; preserve budgets, TLS and fault ordering.
5. **Guard adoption against cumulative regressions.** Screen cheaply, then apply
   the full predeclared gates. Before integration compare with each primary's
   best retained anchor in the same session, not just the last predecessor.
   No repeated attempts on a failed candidate to cross a threshold.

Sources, tools, profiles and executed snapshots remain reproducible. Keep new
results compact and raw detail local according to [RETENTION.md](results/RETENTION.md).
Do not schedule more cache archival as a prerequisite for another tiny candidate.
