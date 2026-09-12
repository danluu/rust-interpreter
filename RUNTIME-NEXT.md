# Next work

Use [STATUS.md](STATUS.md) for the current measured build and controls and
[the September 11 review](docs/SUGGESTIONS-REVIEW-20260911.md) for individual decisions.
Historical plans and failed gates stay in Git and their linked result directories.

1. **Investigate private pointer-value promotion.** Catalog-selected profiles
   pass 340 Rust tests/profile and fourteen real VM commands for seven current
   tests, with exact entropy and logical counts against the retained VM. The
   two dominant token tests have different hot paths; precondition checking and
   generic code expose substantial local memory operations. The existing scalar
   promoter excludes pointers. Review whether private thin raw-pointer values
   can use its existing proof while retaining address-exposure and call-ABI
   exclusions. Keep all checking enabled and preserve legacy promotion capacity.
   [Profiles](results/suite-profiling-real-01/assessment.md),
   [plan](benchmarks/experiments/private-pointer-promotion/PLAN.md).
   Both register-capacity candidates remain parked without retiming.

2. **Preserve the fixed-clear decision.** The fresh combined es8 confirmation
   improves complete commands by 7.39% wall and 7.61% CPU, missing the fixed 8%
   wall gate. All correctness controls pass, but the runtime stays off main.
   Eight original library gates passed; the ninth and remaining composition
   performance comparisons are canceled. Do not retry this candidate to cross
   the threshold. [Decision](results/fixed-frame-clear-combined-01/assessment.md).
   Optional entropy replay qualification is complete; its two-stream A/A
   control does not reopen the parked runtime candidate.
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
