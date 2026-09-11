# Existing test-body compatibility survey

The same compiler build surveyed 3,500 names discovered with the native test
binaries' `--list` option. It lowered 196 bodies. **No test body was executed by
this survey.** Strict Rust checking ran first, and each candidate received its
own lowering graph. These counts are not passing-test counts or whole-project
support claims.

| Project / package | Discovered | Lowered | Blocked |
|---|---:|---:|---:|
| [fre / fre-kernels](lowering-audit-fre-01/summary.md) | 389 | 79 | 310 |
| [Nushell / nu-protocol](lowering-audit-nushell-04/summary.md) | 279 | 47 | 232 |
| [Ruff / ruff_linter](lowering-audit-ruff-01/summary.md) | 2,832 | 70 | 2,762 |

Tool key: `384e561dc2f7114848d98d67e6e18635ed0ca5924115d04833bad1bf1f47cca1`.
Each survey used complete standard-library MIR. The reports retain the pinned
project revisions, native discovery provenance, tool hashes, and per-body first
errors. Rustc's checked queries were shared within each survey; exported guest
functions and allocations were not. Lowering took 1.29 s for fre, 1.48 s for
Nushell, and 14.61 s for Ruff, after ordinary frontend work.

The main implications are:

* Ruff's entry wrapper rejects 2,224 bodies returning non-scalar values, mainly
  `Result`. Add explicit `Result<(), E>` test-result handling, then survey again:
  the current wrapper rejection masks the runtime requirements of those bodies.
* Fre has 216 first failures on mutable/interior-mutable statics. Of these, 140
  occur through `log::max_level` and 75 through CPU-feature selection. Explicit
  thread-local allocation and fault probes account for many more failures.
  Preserving those probes is part of running the real tests.
* Nushell's 88 dynamic-layout failures now concentrate on
  `ArcInner<dyn Error + Send + Sync>`. It also needs mutable state, TLS, and
  randomized hash initialization. Extending nested dynamically sized layouts
  alone will not establish broad Nushell support.
* Current lowering conservatively expands potential calls, including paths a
  particular test might not execute. Each reported error is only the first
  blocker. Counts can shift to another blocker after a fix without increasing
the number of lowerable bodies.

Follow-up: the [Result adapter survey](lowering-audit-ruff-02/summary.md) removed
all 2,224 Ruff entry-result rejections. They became runtime-state failures,
leaving 70 bodies lowerable. Of 2,741 static-state failures, 2,418 first occur
through `fs::get_cwd`. The next prerequisite is guest-owned mutable state,
followed by the OS operations revealed behind those caches. This is a new tool
build; its hashes are recorded in the follow-up report.

The survey exposed and led to fixes for closure instances incorrectly queried
as ordinary functions, thin raw-pointer aggregates treated as struct layouts,
and external constructors whose CTFE MIR was rejected by an optimized-MIR
availability check. Native comparisons cover borrowed/boxed closure dispatch,
thin and wide pointer reconstruction, Arc copy-on-write, and constructors in a
separate crate. The complete differential suite and 75 launcher checks passed.

For execution and speed evidence, the survey selected a larger fre workflow:
all six existing bounded class-sequence tests. After five production refactors,
complete commands measured 0.751 s interpreted, 0.742 s JIT, and 1.322 s native.
Every mode rejected a deliberately incorrect production edit; test source was
unchanged. This workflow uses the installed sysroot.
[End-to-end results](e2e-workflow-fre-class-sequence-01/summary.md).

Subsequent mutable-static support exposed TLS and OS requirements rather than
increasing the Ruff or Nushell totals. Ruff still lowered 70 bodies, with
1,080 first blockers on insta settings TLS, 913 on a test iteration-limit TLS
variable, and further filesystem, mutex, and unwinding requirements. Nushell
still lowered 47, with 133 nested dynamic-layout failures and 43 randomized
hash-state TLS failures. These counts are per-root first blockers, not mutually
exclusive feature requirements across a complete execution path.
[Mutable-state Ruff survey](lowering-audit-ruff-03/summary.md),
[mutable-state Nushell survey](lowering-audit-nushell-05/summary.md).

Adding caller-location propagation after mutable statics increased fre from
79 to 127 lowerable bodies. This includes all twelve existing word64 matcher
tests. The full production-edit benchmark passed those tests but measured
13.164 s JIT and 27.465 s interpreted versus 1.707 s native. The guest executes
5.18 billion bytecode operations; native test execution takes about 0.21 s.
This is an execution bottleneck that the earlier short workflows could not
expose. Runtime optimization now takes priority alongside the remaining
compatibility requirements; the exhaustive inputs stay in the benchmark.
[Caller-location survey](lowering-audit-fre-03/summary.md),
[word64 end-to-end measurements](e2e-workflow-fre-word64-01/summary.md).

Nested dynamically sized layout now raises the nu-protocol survey to 87 of
279 bodies. Of the 40 additions since the preceding survey, 39 previously
stopped at `ArcInner<dyn Error>` layout and one at caller-location support.
The next first blockers include 109 uses of RandomState TLS and 37 uses of
multiply-with-carry. The latter now lowers through compiler-provided Rust bodies
and passes native differential checks, but this survey predates that addition.
The complete last-result group exposed further standard-library initialization
and TLS requirements before execution. No successful guest timing is reported
for that group. [Nested-layout survey](lowering-audit-nushell-06/summary.md),
[full-group blockers](nushell-last-result-blocked-01.json).
