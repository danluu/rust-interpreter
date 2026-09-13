# Reuse-miss and unused-MIR observation — implementation draft

The attached patch is unintegrated and its eight new Rust tests have not run.
It changes five exporter files, preserving the cache format, function-dependency
observer, compiler query order, eager MIR materialization and emitted program.
Apply only after the scalar Copy comparison is terminal and after checking the
recorded source preimage hashes (`git apply --unidiff-zero`). The Python reader
and its eight tests, the launcher and its four tests, and the build/fixture
drivers are also drafts and have not run. Choose the then-qualified VM as a retained
binary; rebuild only the exporter package. Do not overlap builds or diagnostics
with that comparison, mutate its helpers or restart a completed case.

The existing report's204 lowered functions are not necessarily204 red functions.
RUST_INTERP_REUSE_MISSES=0/1 joins existing green/red status to payload presence
before the existing cache lookup consumes the entry. Each function is exactly
one of green-present/reused, green-absent, red-present or red-absent. Each lowered
function is staged or has its recorder's first decline. Red-absent does not
prove a new instance, and no query-edge invalidation cause is invented.

Measure existing preparation, body lowering, clone/template encoding, payload
decoding and binding intervals. A per-function instance of the existing replay
observer records current-context time, nested inside binding. Classify each
already-decoded tape by whether its events need the current MIR body under the
existing resolver. Empty/errno/indirect-shape/unavailable-only tapes do not;
constant/function-pointer/TLS/caller/direct-call events do. Current eager MIR
lookup still runs. Context cost on body-free recipes is an upper bound for a
later lazy-MIR experiment, not a promised saving or a dependency proof.

The diagnostic reconciles every lookup/action total against the original cache
counters, includes cache-load status, caps functions at10,000, labels at4096
bytes and final JSON at16MiB. No second cache-map lookup or record construction
runs when disabled. The flag is tracked in compiler environment dependencies.
Require actual reuse, strict checking, and disabled separate replay-cost,
allocation, function-cost and verification observers. Reject invalid values or
modes before publication. Names/indices identify only this current export.

Qualification, to freeze with executable drivers before running:

1. Review the patch and compile all83 exporter tests in debug and release
   (75 existing plus eight new), then its release binary. Retain the exact
   qualified VM and wrapper; use two Cargo workers, the existing owned host
   target, the shared45-second lock and8GiB floor.
2. Qualify JSON aggregation, missing/duplicate rows, finite/nested phase costs,
   cold/green/red counts, first-decline groups, explicit option routing and
   report bounds in the Python consumer.
3. Run retained/off/on Cargo fixture histories: original, valid, wrong,
   uncalled type error, uncalled borrow error and restored. Require artifact,
   catalog and original outcome parity; no guest launch for compiler errors.
   Cover absent/0/1/invalid options, off/verify/no-incremental cache modes and
   incompatible replay-cost observation. Check option-only Cargo invalidation.
   The draft executable schedule declares28 commands: one lockfile command,
   six states across three modes, three option-only toggles, five invalid/missing
   cache configurations and one incompatible-observer check. Freeze these
   helpers and the chosen retained build before executing.
4. Run one16-command off/on current-token history in fresh namespaces with
   all12 original tests, fixed entropy policy, guest budgets and two prepared
   workers. Admission16GiB, per-command floor8GiB. Require identical bytecode,
   catalogs, tests and source restoration. No timing adoption verdict.

Choose subsequent work from measured costs: recurring green declines versus
red lowering, or avoidable current-MIR preparation. Do not parallelize lowering,
skip graph passes or change the memory model from function counts alone. The
observer itself is not a performance candidate. Private diagnostics are outside
this public-token qualification and private details must remain local.
