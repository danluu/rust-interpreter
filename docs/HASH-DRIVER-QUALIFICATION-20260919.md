# Cached compiler option hashes: driver qualification

The corrected driver compiled and passed both serial and parallel checks. Each
process checked eight option contexts, including tracked, untracked, lint and
reverted options. The parallel run used distinct workers synchronized before
their first hash reads. This qualifies the hash-cache behavior exercised by the
driver; it establishes no application build-time improvement.

The earlier driver failed to compile because its barrier needed rustc's
`IntoDynSyncSend` wrapper. Its failure remains preserved. Across both attempts,
there were four actual top-level children: the failed compilation followed by
the successful compilation and two driver processes.

The independent driver audit is `9540ad45`. The [published evidence](../results/hir-options-hash-driver-02-publication/README.md)
retains the complete archive and recovery references, successful readback, and
the failed archive-processing and archive-audit attempts. The final archive
audit is `6473ffef`; the archive contains 241 members and 13,880,266 logical bytes.

The source files in `experiments/hir-options-hash-driver-stage-03` retain the
exact bytes used by the qualified run. Their original README and STATUS text
describe the proposal before execution and are historical evidence. Six copied
predecessor test files were not rerun against this successor. The separately
qualified catalog and plan-reference helpers passed their 70 focused tests.

The runtime reader's [52 synthetic tests](../results/runtime-prerequisite-controls-04/STATUS.md)
also passed. Full runtime rehearsal, installation, application correctness and
edited-build measurements remain pending. The 0.5-second target has not been met.
