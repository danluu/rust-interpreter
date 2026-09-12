# Exact exporter capability publication

The historical `build.py` source is frozen by completed qualification and remains
unchanged. It rebuilds all components but inherited capability copying from the
VM-only experiment. Consequently a new exporter initially has a stale capability
hash and is correctly rejected by the launcher. Build qualification alone does
not establish launcher readiness.

After this isolated builder, run `publish_capabilities.py --run-id
whole-call-capabilities-NN --build-run whole-call-build-NN` through the supervisor.
It probes the exact built exporter under both publication/benchmark locks, checks
the capability semantics, binds the new exporter hash and exercises every launcher
option guard. Preserve the before/after receipts; binaries, source and ready
manifests must remain byte-identical. No compiler rebuild or guest execution.

For this candidate the build is 02 and publication is 01. Its first failed export
admission is preserved as `whole-call-export-smoke-01`. Benchmark admission must
require the successful publication receipt in addition to the build and smoke
qualifications. Normal `scripts/interpreter.py` already probes new exporters and
does not have this experiment-local bug.
