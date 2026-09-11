# Attribute frontend/build work before changing its execution path

Current 78e60cdd versus b2 held-out measurements show little change on frontend
workflows. Nushell type relations has a 5.159 s candidate command median, 5.082 s
in Cargo and 0.01044 s in guest execution. Its generic-constructor edit is being
measured separately. These values bound the benefit of JIT tuning for these
workloads; they do not identify a removable compiler dependency.

An older, different-tool float-range profile already captured three nu-protocol
units: a native host library with `os,os_pipe`, an ordinary checked library with
`default,os,os_pipe`, and the checked test target. Downstream checks and the
nu-cmd-extra build-script chain also run after source changes. That build script
imports the shared HtmlTheme definition, whose IntoValue derive uses nu-protocol.
Do not remove this dependency, skip host work, or infer that identically named
units can share artifacts. Feature sets, target contexts and compiler modes matter.

The completed current-tool interface qualification's
[fingerprint inventory](../../../results/compiler-unit-fingerprints-01/summary.json)
has three nu-protocol fingerprints in **all four** histories: native, independent
check, baseline and candidate. Native/check commands apply the repository's
`-Ctarget-cpu=apple-m1` flag to their units. The explicitly targeted custom build
has that flag on target units, while its host library has no recorded rustflags.
Profile hashes also differ. This read-only inventory starts no compiler and is
not per-edit timing, but it rules out attributing the three-unit count solely to
the custom engine's explicit `--target`. Do not pursue a sysroot/target change
on that assumption. Inspect actual unit profiles and dependencies first.

Use the existing `bench_e2e_workflow.py --cargo-timings` path with the pinned
Nushell generic-interface case, one complete cycle and all original tests/wrong
edits, b2/78 JIT options, native 18 jobs/O0/incremental/default test concurrency,
custom four jobs, std-MIR and strict checks. Keep its fresh cache history and
instrumentation separate from the fifteen-cycle performance measurements.
Expect nine primary timing snapshots and three independent checking controls;
the checking controls do not enable Cargo HTML instrumentation.

First qualify `cargo_timing_data.py` against the four retained original Cargo
captures and malformed/overlap cases. Then verify the new workflow's source,
artifacts and receipts and run `analyze_cargo_timings.py` over its hashed HTML
snapshots. It parses JSON only; it never evaluates the embedded JavaScript.
Keep every compiler unit ID, feature set, target description, duration and
reported section, plus duplicate grouping keys and unblocking IDs absent from
the observed intervals. Cargo currently labels many modes `todo`; that string
does not establish a compiler mode. A section named `codegen` in a check target
does not prove LLVM ran. Cross-check any host/target attribution with Cargo's
actual compilation graph/commands before drawing that conclusion.

Compilation intervals overlap. Report their union and overlap separately from
per-group elapsed sums; neither is CPU time or a causal critical path. Preserve
cold and wrong-edit captures. Do not turn unobserved warm units into measured
executions or collapse two matching units into one dictionary entry.

This chooses the next implementation by actual scope:

- If repeated compiler processes have material routing/startup overhead,
  investigate a small Rust wrapper that execs ordinary rustc for provably
  unselected units, loading rustc_driver only for export. Preserve exact std-MIR
  argument transformation, host tools, Cargo jobserver/environment, exit behavior
  and selection invalidation. A bad route must never execute a stale sidecar.
  Qualify this separately; do not claim that all unit time is wrapper overhead.
- If actual checking/expansion or dependency propagation dominates, work at those
  compiler/build boundaries. Removing export work alone cannot remove needed
  type/borrow/layout checking or generated-code dependencies.
- For execution usability, the full-suite requirement remains open. Fresh fre
  replay covered 382 bodies individually with seven ignored, not a full libtest
  command. A broader shared test graph needs correct entry/attribute/state
  semantics and explicit unsupported outcomes; do not substitute a successful
  supported subset for the whole requested suite.

No runtime change or retention decision follows from this diagnostic alone.
Both original token gates remain failed. No LLVM/external guest backend,
unchecked lazy execution or fake synchronization/unwind behavior is introduced.

Status: `compiler-timing-parser-01` passes four preserved captures, nineteen
malformed inputs and synthetic overlap/feature/duplicate checks. Both repeated
interface runs and the nine-snapshot instrumented comparison are complete and
verified. The lightweight wrapper's warm comparisons are complete; four of six
fixed cold histories are verified. The [futility bound](../../../results/lightweight-wrapper-cold-futility-01/assessment.md)
proves its 5% cold gate unreachable; the two unstarted histories are stopped and
the original six-history protocol is marked incomplete. No wrapper retention.

[Cold timeline inspection](../../../results/compiler-cold-concurrency-01/assessment.md)
now finds 800 custom timed Cargo units under four jobs versus 608 native units
under eighteen jobs. Custom cold CPU/wall is about 3.1, versus about 1.5 after
the API edit. Reported overlap is broad during cold commands and much narrower
after edits; it does not reveal a ready queue or establish a critical path.
This makes an isolated custom-worker-count comparison a candidate next direction
after the fixed wrapper comparison. Do not change its current four-job controls
or infer that the extra host/target units are interchangeable. A subsequent
experiment must freeze one tool in both arms, qualify mode-specific job recording,
predeclare its cold/warm samples and criteria, and retain all original assertions,
wrong edits, independent checks and artifact comparisons. Stable allocation and
relocation identity remains necessary before pursuing function-level reuse.
