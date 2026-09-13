# Cargo setup diagnosis, continuation 03

The trace identifies a concrete compiler-info cache failure, but setup memoization alone does not account for the gap to 0.5 s. Cargo reports that its compiler fingerprint fails on an empty workspace-wrapper path, disables its existing rustc-info cache, and executes all five information probes again. The normal launcher also exports an empty workspace wrapper, so this observation has production relevance beyond the diagnostic wrapper.

| State | Cargo wall s | Cargo child CPU s | VM wall s | rustc phase logging | Original tests |
| --- | ---: | ---: | ---: | --- | --- |
| edited | 5.898274 | 10.813951 | 0.012747 | True | 14 passed |
| restored | 4.172439 | 7.753052 | 0.012847 | False | 14 passed |

Both commands include Cargo Chrome tracing, rustc-info debug logging, `-vv`, Cargo HTML timings, exporter timers and the Python diagnostic wrapper with process receipts. Only the edited command adds rustc phase logging. The source and cache states differ, so subtracting restoration from edited time does not estimate profiler overhead. These direct Cargo/VM observations exclude normal launcher startup and setup and do not establish a normal startup floor or a speedup.

This is fresh edit 3 relative to the recorded diagnostic target history, continuing [self-profile 02](../strict-warm-self-profile-02/assessment.md) and its existing profile-01 target. No new cold prime was run. This is not an independent cold history, a new-project holdout, or acceptance evidence.

| Elapsed scope | Edited s | Restored s | Interpretation |
| --- | ---: | ---: | --- |
| Cargo main before job queue | 0.645299 | 0.403473 | Same-thread elapsed prefix; excludes later scheduling and replay |
| First compilation wrapper from parent Cargo start | 0.764621 | 0.498439 | Process receipts; includes instrumentation/startup |
| Compiler-info setup interval union | 0.176610 | 0.171237 | Three Rustc::new scopes plus nested target-info scopes, overlap removed |
| Three Rustc::new scopes | 0.111333 | 0.105101 | Includes -vV waits and wrapper overhead |
| Five probe child intervals | 0.056067 | 0.058449 | Wrapper waits for child, not CPU |
| Job queue execute | 5.222251 | 3.736579 | Includes waiting for concurrent compiler/build-script work |

Rows overlap and must not be added. In particular, the job-queue span is not several seconds of Cargo CPU. Same-thread self elapsed time subtracts directly nested spans; it can still include blocking and waiting. Sums across threads can exceed command wall time. The separately recorded Cargo child CPU above includes descendants and is not a Cargo-only CPU measurement.

Each trace has 30,451 matched spans and 213,171 events. Its 36 `rustc` spans consist of 18 on the main thread and 18 on worker threads; these are span entries, not 36 compiler processes. Independent wrapper receipts identify 18 real compiler invocations and five information probes per state. Cargo HTML reports those 18 compiler units plus one build-script execution. Synthetic trace PID 1 and thread indices are not operating-system process identities. The selected test role is confirmed through exporter arguments and the selected Cargo artifact, since incoming wrapper arguments alone need not contain `--test`.

## What can safely improve

Both stderr logs contain three fingerprint failures naming the empty path, three cache-disabled messages, five cache misses and five actual query commands: three identical `-vV` calls, one host-information query and one explicit-target query. The captured environment has `RUSTC_WORKSPACE_WRAPPER=""`. The archived production launcher sets the same value.

The concrete first candidate is Cargo-side normalization of the explicit empty workspace wrapper when constructing its compiler fingerprint, after configuration resolution, while preserving the meaning “disable the configured workspace wrapper.” Merely deleting the launcher environment value could activate a wrapper from Cargo configuration and change behavior. A fix should let Cargo’s existing cache retain its normal rustc/wrapper/target/flags invalidation. The trace identifies the failure path; this package contains no implementation or evidence that the proposed change restores hits.

The observed compiler-info interval union is 0.177/0.171 s, or 4.1% of the restored instrumented command. Treat that entire scope as an optimistic removable-work budget, not a prediction: validation still costs time, and these scopes contain Python startup, receipt I/O and other diagnostic overhead absent from the production wrapper. Sharing duplicate in-process Rustc setup addresses only part of that budget. The two later Rustc::new scopes total 0.065/0.072 s here.

Even eliminating the entire observed prefix before the first compilation wrapper, while holding subsequent work fixed, would leave 5.134/3.674 s of these commands. That arithmetic is an illustrative budget, not a latency forecast: a real change can alter scheduling and overlap. It shows why resolving this cache failure may give a useful small general improvement, while compiler and dependency work still needs much larger reductions for the target.

Broader memoization of dependency resolution, manifest parsing and fingerprint planning would need to preserve Cargo configuration/environment changes, feature/target/profile selection, source and dependency freshness, build-script rerun rules and proc-macro recompilation. The trace does not establish those checks as safely removable. Recursively nested fingerprint spans especially must not be summed into an alleged saving.

## Largest exclusive elapsed labels before the job queue

These clipped same-thread values are descriptive elapsed attribution, not sampled CPU or a claim that a check can be omitted.

| Category / span | Edited s | Restored s |
| --- | ---: | ---: |
| `cargo::compiler::fingerprint::calculate` | 0.143371 | 0.028650 |
| `cargo::util::rustc::new` | 0.111333 | 0.105101 |
| `cargo::compiler::fingerprint::prepare_target` | 0.088494 | 0.016115 |
| `cargo::resolver::resolve` | 0.067167 | 0.066804 |
| `cargo::compiler::build_context::target_info::new` | 0.065278 | 0.066135 |
| `cargo::compiler::build_runner::prepare` | 0.027709 | 0.002780 |
| `cargo::compiler::build_runner::compile` | 0.026389 | 0.004090 |
| `cargo::workspace::package::download_accessible` | 0.017617 | 0.018199 |
| `cargo::compiler::compile` | 0.008754 | 0.007019 |
| `cargo::workspace::parser::parse_document` | 0.007368 | 0.007570 |

## Evidence

[summary.json](summary.json) contains exact identities, source/test validation, all actual compiler roles, probe receipts, recomputed trace aggregates and startup spans. [report.json.gz](report.json.gz) preserves the complete original diagnostic report. [evidence.json.gz](evidence.json.gz) preserves exact command/process receipts, stdout/stderr, suites, artifact sidecars, HTML timings, frozen harness/tool provenance and the original derived trace summaries. Both raw 60 MB Chrome traces are retained in separate deterministic gzip files named in the summary; each decompresses byte-for-byte to its recorded original SHA256. No raw trace events are sampled or discarded. The independent parser reconciles all B/E spans and aggregate counters with the saved summaries. Trace arguments were not captured; compiler argv is instead retained in the wrapper receipts.

Tool key: `923ad6d94c365365f15322ee65d32dca6ba9ccc4fd07a8147111329ea1955c86`. Pinned compiler: `rustc 1.100.0-nightly (cea272fa3 2026-09-07)`. Nushell and compiler/sysroot identities and the prior-report hash are in the JSON. Cargo has prior optimization exposure and is already excluded from fresh holdouts, as recorded in [CARGO_EXPOSURE.md](../../benchmarks/experiments/strict-warm-build/CARGO_EXPOSURE.md). No holdout workload was executed for this diagnosis.

Repackage the saved evidence without executing a workload:

```sh
python3 benchmarks/experiments/strict-warm-build/assess_cargo_trace.py \
  /Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/strict-warm-cargo-profile-03/report.json \
  --trace-run /Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/strict-warm-build/cargo-trace-01/summary.json \
  --run-id strict-warm-cargo-profile-03-reproduced
```
