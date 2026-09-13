This follow-up formats tree-validation error paths only when a check fails. The predicates, exception types, messages, complete traversal and all identity checks remain unchanged.

All 33 compiler/std and inventory-refusal controls passed again after this source change. Five alternating paired samples of complete compiler plus shared-std loading reduced median wall time from 157.917 ms to 111.974 ms (CPU 157.811 ms to 111.893 ms). All returned values and readiness records matched exactly. Baseline source is 151af48b; candidate source is 7103301f.

This measures only the compiler/std loaders and excludes tool loading, Cargo and VM execution. It makes no end-to-end or sub-0.500-second claim. The previous traversal comparison remains separate in ../owned-tree-validation-01.

All ten samples, raw process/supervisor receipts, tests, exact helper source and readiness bytes are retained. Every archive member was read back and verified. No compiler, standard-library installation or Nushell source was changed; no holdout ran.
