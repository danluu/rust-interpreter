# Frontend optimization status, September 19

Neither compiler candidate below has a measured application speedup yet. No new
result establishes a warm edited build below 0.5 seconds. Correctness checks and
installation work are separate from application build timings.

| Candidate | Completed checks | Remaining performance evidence |
| --- | --- | --- |
| Cache the immutable incremental option hash once per compiler context | Compiler build; serial and parallel hash controls; compiler behavior controls; runtime preflight and its independent saved-result audit | Complete runtime installation and composition, then real edited Ruff builds with HIR caching off/on and independent holdouts |
| Retain the first ordinary procedural-macro arena page across reset | Corrected native and Miri checks; real macro callers against both N client libraries; default sysroot discovery with matching dependency evidence | Complete the fixed Ruff native frontend screen; pursue application qualification only if its gain exceeds the measured stock/stock variation |

The hash candidate retains the complete original hash and its wire encoding.
The arena candidate retains only an ordinary first page after clearing interned
references. Neither change selects applications, omits compiler checks, or edits
Ruff or Nushell to obtain a speedup.

The next arena measurement has six blocks, twelve stock/candidate pairs and six
stock/stock pairs: 36 timed compiler calls. Untimed warmup, restoration and Cargo
setup remain separate. A native nonincremental frontend screen cannot establish
the full interpreter edit-to-run target.

The first two screen attempts stopped during Cargo setup. Attempt 01 rejected
Cargo's ordinary `-Z embed-metadata=no`; attempt 02 rejected a build-script
command with no `-C extra-filename`. Attempt 02 completed three compiler queries
and one dependency compilation. Neither attempt reached an edit, warmup or timed
sample. Their original arguments and failure records remain retained; successor
harness changes must preserve those arguments and the fixed comparison rule.

Evidence entry points:

- [Option-hash change and semantics](hir-options-hash/README.md)
- [Actual serial/parallel driver controls](../results/hir-options-hash-driver-02-publication/STATUS.md)
- [Passed saved runtime preflight audit](../results/runtime10-preflight-saved-audit-01/STATUS.md)
- [Passed installation resource and admission controls](../results/runtime-installation-controls-07/STATUS.md)
- [Actual macro-client default discovery checks](../results/proc-macro-arena-n-overlay-01-publication/STATUS.md)
- [First Ruff setup failure](../results/proc-macro-arena-ruff-screen-01-publication/README.md)
- [Second screen's frozen source and protocol](proc-macro-arena-ruff-screen-02/README.md)

Historical plans and source manifests retain their original status text. The
linked actual-result records establish which work has since run; an old plan's
test count is not a new execution result.
