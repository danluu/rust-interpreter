# Fresh profiles after complete held-out qualification

Finish all seven fixed guards, including the declared complete Ruff retry,
before selecting another runtime implementation. Keep the incomplete Ruff
history excluded and preserve any completed regression. Passing these selected
workflows is not full-suite support or automatic production-source adoption.

If the candidate passes, profile the exact `9637b0ac` artifacts from the
original-source state of both completed primary comparisons. Its VM remains
the immutable `21d1e163` binary from tool `0e94d6d8`; only the exporter changed.
Bind each artifact to its actual primary record, immutable binary hashes and
completed comparison. Do not rebuild or edit the guest test to make it last
longer. Keep original assertions, RNG, 150,000 allocations, persistent registers,
resumable calls and default instruction budget.

Reuse `scripts/sample_owned_vm.py` for three owned executions each: one-second
sample windows for folded, three seconds for token, with `--dump-code`.
Serialize these with the benchmark lock. Wait for every owned VM and diagnostic
child to finish naturally; do not sample or control another process. Reuse
`summarize_owned_sample.py` and `attribute_generated_sample.py` to bind sampled
addresses to each execution's own live mappings and emitted code. Preserve
partial or failed sampling attempts instead of replacing them silently.

Report captured self-sample categories and unresolved PCs. Compare with the
earlier `resumable-copy-{folded,token}-sample-01` reports as descriptive context,
not matched performance measurements or predicted speedups. Choose the next
substantial implementation from the remaining observed costs, then declare its
correctness envelope and complete-command performance gates before measuring.

Source inspection found duplicate scalar-frame analysis in aggregate capture:
`scalar_frame::pack` computes shapes, liveness and slots; `byte_writes::capture`
recreates the old scalar visitors/layout/planner to check those same slots.
A future cleanup could carry that result forward with explicit unchanged-slot
checks. It must preserve conservative byte-write proofs and independent new
physical-layout validation. This is not the next runtime strategy by default:
the entire recorded capture stage is only about 95 ms in a 4.46 s token command,
and only part of it is duplicated work. The 189.5 ms capture/finalization total
also omits some earlier instrumentation costs. Keep these observations separate
from measured savings; do not turn another small compiler cleanup into a claim
that compute-heavy tests now approach native performance.
