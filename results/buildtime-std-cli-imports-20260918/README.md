Stock standalone std setup now imports custom compiler and Cargo installers only when selected. The fixed prepared-cache experiment passed all eight gates: component CPU ratio 0.961175 with 18/20 paired wins, and all 21 correctness tests passed.

See [the evidence report](evidence/README.md) for exact source, raw records, audits, and measurement limits. This measures the instrumented stock CLI path with compiler discovery stubbed; it establishes no full-build or holdout speedup.
