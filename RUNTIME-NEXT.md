# Next work

Use [STATUS.md](STATUS.md) for the current measured build and controls and
[the September 11 review](docs/SUGGESTIONS-REVIEW-20260911.md) for individual decisions.
Historical plans and failed gates stay in Git and their linked result directories.

1. **Finish the fixed-clear retention gates.** The bounded store sequence for
   statically known frames up to 256 bytes is implemented on
   `experiment/fixed-frame-clear`. It still clears every byte and alignment
   gap. The [three-history confirmation](results/fixed-frame-clear-confirm-02/assessment.md)
   improves complete es8 edit/build/test commands by 8.37% wall and 8.48% CPU
   across 15 pairs, excluding the pilot. Per-history wall gains range from
   7.10% to 9.07%; candidate execution remains roughly 2.5 times native.
   All 47,004 native differential commands, 245 TLS checks, 382 fre bodies
   (seven ignored) and 52 integration assertions pass. Run the nine original
   library workflows with independent 5% wall/CPU regression gates before
   merging the runtime change. Pgrust, folded fre and token pass; token saves
   3.43% wall and 3.32% CPU, while the first two show near-zero differences.
   [Progress](results/fixed-frame-clear-libraries-01/summary.json) records all
   remaining cases. Each comparison requires identical bytecode. After these
   isolated-VM gates, qualify composition with the newer main interpreter loop.
   The [execution plan](benchmarks/experiments/frame-initialization/FIXED-WORKFLOWS.md)
   allows smaller cases first when storage admission prevents larger builds.
   Integration coverage now includes
   all 52 fre assertions. The short end-greedy edit pilot gains 20.4%, but es8i
   costs 3.867s custom versus 1.449s native (2.678× paired). Native uses default
   threads; custom batches are sequential. Three owned es8i profiles place
   98.33% of samples in generated code and 14.81% in clearing. The conservative
   [initialization proof](results/frame-initialization-proof-01/assessment.md)
   covers only 3 of 1,135 clearing samples, so elision stays diagnostic. A bounded
   sequence of stores for statically known extents up to 256 bytes covers 1,041
   samples and motivated the current candidate. Its targeted checks include
   16,448 dirty host buffers plus guest alias, alignment and exact-limit cases.
   Keep the native doc-test failure and incomplete libtest semantics visible.
2. **Choose substantial export work from measured costs.** The retained observer
   produced seven byte-identical token artifacts. Graph lowering costs 691ms;
   hashing/publication/serialization/validation together cost about 98ms. Do not
   run full primaries for those small components. Diagnose allocation-order
   determinism before designing semantic graph reuse. The scalar ABI remains
   parked after its 0.74% gain missed the 8% screen.
3. **Keep native controls and suite semantics explicit.** Fre native calibration
   missed its fixed 8% screen (line tables saved 7.86%); do not repeat it. Compare
   a large frontend-dominated target separately. Pgrust/Ruff already use line
   tables; all five projects use unpacked split info. The unfiltered command
   includes integration and rustdoc targets. Direct library-body coverage is
   insufficient; implement per-test state/TLS/ignore/failure handling and report
   unsupported harness features. Model any hybrid at Cargo-target granularity.
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

Merge qualified changes to `main` and push regularly to the private
`danluu/rust-interpreter` repository. Parked source branches stay separate.
