# Arena04 through a real compiler proc-macro dylib

This fixture is source-only and uncompiled. `plan.json` contains the exact
unexecuted argv, environments, output routes, bounds and diagnostic expectations.
It proposes the same macro and caller sources for two arms: installed stock
`proc_macro`, and the already-built normal Arena04 library. Both use the
unchanged matching `nightly-2026-09-08-aarch64-apple-darwin` compiler and sysroot.
No existing installation, provider or prior library is modified.

The candidate client is
`ROOT/.work/proc-macro-arena-bridge-01/libproc_macro.rlib`, saved SHA
`d305e270a253943004c91f3f24a293fe7116333c469f3b8fc766d29ab3b02b25`.
Its sibling real `rustc_literal_escaper` is resolved through only that directory's
`-L dependency` path. The stock arm explicitly names the installed matching
`libproc_macro-9dac517e5d77c501.rlib` and `.rmeta`. The normal candidate library
and installed stock library have different build provenance; this is a behavior
comparison, not a controlled performance experiment.

Each arm first builds `macros.rs` with `--crate-type=proc-macro` and its explicit
`--extern proc_macro`. The compiler-generated proc-macro harness resolves that
ordinary extern through the same exact-path mechanism as the fixture's public
types. Transitive dependency hashes and ordinary compiler checks stay enabled.
Then separate caller compilations use only the arm's exact new dylib via
`--extern arena04_macros`, producing metadata. These commands execute the real
macro client through the installed rustc server; they do not substitute a mock
Server or qualify a new compiler distribution.

`macros.rs` uses stable public `Ident`, `Literal`, `TokenStream`, `Group` and
`Span` APIs. Every successful exercise keeps early values alive while creating
96 distinct identifier/literal pairs, an 8193-byte identifier, an 8193-byte
literal and another small identifier, then checks their exact strings and
spans. It checks raw/Unicode identifiers, escaped Unicode strings, real token
serialization/parsing and source-backed input spans. These operations exercise
the real client's interner; there are no arena counters, models, unchecked
references, internal feature gates, timings or memory-use assertions.

The nine caller cases per arm are:

- Default success: repeated function-like expansions, an emitted nested
  expansion, attribute passthrough, derive output and const-evaluated values.
- The same success caller with explicit same-thread execution.
- Default explicit diagnostic, with its span placed on the input identifier.
- Default deliberate panic after nonempty symbol work.
- Default ordinary type mismatch (`E0308`) and borrow conflict (`E0502`).
- Same-thread stale identifier and stale literal, each returned through a
  second compiler-scheduled invocation and required to fail with the exact
  symbol invalidation message.
- Same-thread panic followed by a callback that requires the earlier panic
  flag, performs new symbol work and emits a distinct marker diagnostic.

Only the explicit TLS cases and extra success case use the source-supported
`-Zproc-macro-execution-strategy=same-thread`. All other cases retain the
compiler's default strategy. The nested caller tests compiler-scheduled
successive expansion, not simultaneous reentrancy; the existing bridge suite
covers controlled reentrant calls. Panic recovery is established only if the
later marker is actually observed in that compiler process. No default-strategy
recovery-order claim is made.

Expected outcomes are in `plan.json`: both dylib builds and both success cases
must return zero, and the seven negative cases must return one with their exact
primary error set. Full raw JSON diagnostics must be retained. Comparison uses
stable code/message/help and primary source-span fields, not rendered text or
timings. Metadata must exist only for successful callers. Successful caller
dep-info must bind its exact dylib; dylib dep-info must bind the selected client
library (and the candidate's real literal dependency), never the opposite arm.
All chosen artifacts and source hashes need current readback before execution
and recheck afterward; saved hashes here are not a claim of a new readback.

There are exactly 20 proposed compiler children, run serially under the
canonical lock. The plan retains the existing 24 GiB compiler entry policy,
9 GiB live stop, 8 GiB floor and 600-second lock wait. Per-child bounds are
120 CPU/180 observer seconds for dylib builds and 30 CPU/60 observer seconds
for callers, with a 64 MiB file limit and 128 MiB aggregate fresh-work limit.
The outer bound is 2400 seconds. No signals, retries, library copies into a
sysroot, toolchain updates or peer process control are proposed. An observer
expiry must preserve an explicit potentially-live child rather than claim
closure. No execution wrapper or general audit framework is added here.
