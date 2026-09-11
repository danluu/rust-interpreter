# Staged worker-count controls

The standalone helper passes six configuration checks, 48 malformed-input/
receipt/command rejection checks and sixteen argparse rejection cases. The
seven preserved histories contain 756 commands whose recorded worker counts
agree with the helper's historical interpretation. These commands were inspected,
not rerun. New per-mode counts preserve native/check defaults independently.
Duplicate worker options and contradictory executed counts are rejected.

The helper and qualification driver are new files. Neither is imported by the
frozen wrapper benchmark, its launcher, or its verifier. Actual harness integration,
early CLI qualification and new project executions remain pending until all six
wrapper cold histories have been assessed. This is correctness groundwork for
the [worker-count experiment](../../benchmarks/experiments/compiler-pipeline/WORKER-COUNT-NEXT.md),
not a performance result or a qualified change to benchmark execution.

[Exact checks and source hashes](summary.json).
