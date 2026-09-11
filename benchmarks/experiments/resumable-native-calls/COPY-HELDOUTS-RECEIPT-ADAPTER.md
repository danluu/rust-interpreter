The frozen aggregate runner rejected an extra `_specified_job_counts` key in
all seven actual corpus option dictionaries. It is emitted by `workflow_jobs.py`
and records that `--jobs` and `--native-jobs` were explicitly supplied, in that
order. All planned option values and frozen script hashes match. The individual
case gates pass; the original aggregate failure remains preserved.

The earlier aggregate qualification exercised constructed component fixtures
and individual case evaluation, but did not exercise this strict comparison
against an actual corpus plan. The new receipt adapter requires exactly
`['jobs', 'native_jobs']` in addition to every original option. It does not ignore
unknown metadata, alter measured receipts, or relax any performance criterion.

`COPY-HELDOUTS-RECEIPT-ADAPTER.json` binds the new two source files and preserved
failure. The original plan, retry amendment and all original evaluators remain
unchanged. The collection runner retains their source, artifact, admission and
complete-set checks and delegates gate evaluation and combination to the same
original functions. The only option-schema extension is the explicit job list.

Qualification now uses all seven actual corpus plans, reproduces their existing
per-case receipts and both primary comparisons, rejects 27 invalid inputs and
preserves a deliberately regressed case. No benchmark is rerun. This adapter is
required for the final `resumable-copy-heldout-recovery-01` aggregation.
