# Next work

Use [STATUS.md](STATUS.md) for the current measured build and controls and
[the September 11 review](docs/SUGGESTIONS-REVIEW-20260911.md) for individual decisions.
Historical plans and failed gates stay in Git and their linked result directories.

1. **Test frame-initialization proof coverage.** Integration coverage now includes
   all 52 fre assertions. The short end-greedy edit pilot gains 20.4%, but es8i
   costs 3.867s custom versus 1.449s native (2.678× paired). Native uses default
   threads; custom batches are sequential. Three owned es8i profiles place
   98.33% of samples in generated code and 14.81% in clearing. Count eligible
   clearing sites under a conservative stronger initialization proof before
   implementing elision. The old argument-only idea stays parked. Preserve
   caller-local source proofs, unknown-pointer aliases, padding and exact limits.
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
