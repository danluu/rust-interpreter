The compiler/std installation validator now uses one no-follow stat per file and rechecks every directory after traversal. It still enumerates and validates every entry on every call; all six identity fields, immutable-file checks, key validation and source/configuration guards remain. No persistent cache or root-only shortcut was added.

All 33 controls passed, including unchanged compiler/std loader tests and six new inventory/refusal controls: nested changes, same-size/mtime-restored content changes, links, special files and a directory replaced by a symlink during traversal.

Five alternating paired samples of complete compiler plus shared-std loading reduced median wall time from 454.980 ms to 167.079 ms (CPU 451.494 ms to 166.977 ms). Every returned value and existing readiness manifest matched exactly. This measures only those loaders; it excludes tool loading, Cargo and VM execution and makes no end-to-end or sub-0.500-second claim. Baseline source is 85b56435 and candidate source 151af48b.

The archive retains all tests, ten samples, raw process/supervisor receipts, exact baseline/candidate helper source and readiness bytes. Every member was read back and verified. The existing compiler, standard-library installation and Nushell source were unchanged; no holdout ran.
