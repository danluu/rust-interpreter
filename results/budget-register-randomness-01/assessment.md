# Token workload randomness and profile accounting

An additional identical-control execution with unchanged flags and bytecode confirms varying instruction counts. Actual RandomBytes operations execute in every captured token profile. The original VM calls CommonCrypto for entropy; the diagnostic does not replace it or edit the guest.

All three profiled executions reconcile their per-PC interpreted/native counts exactly to their own instruction totals, and all original assertions pass. Independent entropy makes cross-process path/count equality and a previous execution's exact total-minus-one budget inappropriate controls for this workload. Deterministic focused fixtures retain exact count/budget equality; real random workloads retain per-run accounting and fixed short-budget failures. No performance threshold changes.
