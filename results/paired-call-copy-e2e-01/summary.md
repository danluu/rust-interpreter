# Paired production-edit commands: local call copies

Both immutable JIT builds run each of five real production refactors with independent Cargo caches. Original tests remain unchanged. All modes reject a deliberately wrong edit. Executed bytecode is identical within every comparison, including cold and negative runs; snapshots and per-command hashes are retained.

| Workflow | Native median (s) | Baseline JIT (s) | Candidate JIT (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|
| [pgrust hashing](../e2e-paired-pgrust-call-copy-01/summary.md) | 0.644 | 0.547 | 0.543 | -6.2 | 5/5 |
| [fre word64](../e2e-paired-fre-word64-call-copy-01/summary.md) | 1.726 | 3.088 | 2.991 | -162.4 | 4/5 |
| [fre word64, MIR inline scale 8](../e2e-paired-fre-word64-inline8-call-copy-01/summary.md) | 1.970 | 2.542 | 2.507 | -35.1 | 4/5 |
| [pgrust SHA-1, MIR inline scale 8](../e2e-paired-pgrust-sha1-inline8-call-copy-01/summary.md) | 0.742 | 1.233 | 1.212 | -24.9 | 4/5 |

The selected change improves 17 of 20 measured pairs. The native control remains faster for word64 and SHA-1; pgrust hashing favors the custom JIT. Five edits on a shared host are a small sample, not a confidence interval. Difference-of-medians and median paired differences are distinct statistics. Independent Cargo caches and host scheduling can still affect a pair.

Timers include Cargo, export, launcher artifact hashing, JIT construction, and test execution. Snapshot copying follows the timer. Cold runs exclude tool bootstrap, downloads, installed sysroot preparation, and OS file-cache coldness. This is a selected-test workload comparison, not a full-application or full-suite result.

The launcher now supports `--tool-key`; the benchmark supports `--baseline-tool-key`, `--comparison-engine`, and `--expect-identical-bytecode`. The pinned-tool path and original three-mode path pass 99 launcher checks and a separate production workflow regression.

Example:

```sh
python3 scripts/bench_e2e_workflow.py --project pgrust --batch \
  --baseline-tool-key ae1110085889bb1b67425ff5e2d066cd73b75560ac2abdfcc41be00ff320d328 \
  --comparison-engine jit --expect-identical-bytecode --run-id YOUR_UNIQUE_RUN_ID
```
