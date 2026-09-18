# Prospective runtime integration

This is an integration plan, not an adoption decision. The candidate is tool
45a1529e / VMfd21a46f. It combines native indirect transitions, checked readonly
scalar leaves and successor-only spilling on the adopted scratch/scalar runtime.
All five project histories pass726 commands; the parser guards are still pending.
The separate project closure verifies9,290 frozen inputs and122 source bindings.

Before integration require all five complete project histories (726 commands),
all114 original parser tests and both88-command edited-parser guards. Preserve
every failed setup, host-feature diagnostic and audit-lock timeout. Audit-only
checkpoint recovery never supplies a new performance pair. The final closure
must have both `all_five_gates_passed` in its summary and `candidate_qualified`
in its closure; a passing project history alone is insufficient if a parser
guard fails. Keep the current main runtime on any failed gate.

Only after closing those results, freeze a current-main integration revision.
Preserve the other session's compiler-selection, standard-library setup, Cargo
and benchmark work. The last inspected main was237510c3; fetch again when
integration is actually admitted. Never force-push or overwrite peer changes.

Main now includes2ba26966: bounded leaf-eligibility scans, shared call-graph
facts and a summary-only CFG pass used by the exporter. These are production
Rust changes, including in the bytecode crate linked into the VM. Preserve them
when integrating the runtime delta. The frozen VM/exporter qualification cannot
establish correctness or performance of the new combined binaries. Build and
qualify the actual merged sources, including the peer's inlining/CFG controls,
strict/cache workflows and exact real-workload artifacts/profiles. Any claim
about combined performance needs a new matched changed-source comparison
against current main, with the protocol declared before timing. Keep the frozen
campaign's result and attribution separate from that prospective comparison.

Main091f9ea9 also replaces Path-object construction with canonical POSIX ancestor
scans in runtime collision validation. Its tests cover nested collisions and
non-collisions. Preserve those tests with the runtime-option forwarding tests;
this is an additional reason not to copy the frozen scripts over current main.

The measured Rust/Cargo/configuration inputs must remain byte-for-byte equal to
the candidate build. Installed VM, exporter and wrapper digests must also match.
Any different Rust/compiler implementation needs new qualification, not a new
label on the old evidence. Keep indirect and scalar calls explicit, require the
fully checked resumable JIT, and preserve the16MiB arena and two-worker settings.

Recovered checkpoints2/3 retain exact copies of their campaign ledgers. Their
original evidence manifests also referenced the live ledger, which grows when
later cases finish. The prepared checkpoint-evidence repair resolves those two
references to the already captured immutable copies, verifies every original
digest, and retains the original receipts. Require its successful supplemental
proof when auditing those intermediate closures; it changes no measurement.

If the final Nushell supervisor encounters the same post-case lock timeout,
recover_final_audit.py can verify all726 existing commands and finish the audit
without executing a guest. It requires the exact failed terminal/log, preserved
four-case checkpoint, complete fifth-case record and all unchanged inputs. It
retains a failed performance gate as a rejected campaign. The recovery's successful
audit status does not turn a failed performance gate into a pass. If used, bind
its separate plan, original failure, recovery terminal and Git source when closing
and integrating the final campaign. The recovery remains unexecuted; the final Nushell supervisor completed normally.

close_projects.py can separately close the726-command project evidence before
parser qualification. Its explicit `parser_guards_complete: false` and
`runtime_adopted: false` prevent that receipt from becoming an adoption decision.
This also permits verified retirement of completed project compiler caches if
the fresh parser histories need disk space. Final closure and integration still
require the original parser guards, and all retained project artifacts stay intact.

The three completed Nushell custom compiler namespaces were retired after
free space fell below parser admission. The deletion controller verified the
project closure, exact132-command evidence, source restoration and namespace
locks/open files. Its later close audit verifies33,924 removed paths absent
and20,095 protected hashes unchanged. Native/parser/shared/private/peer caches,
executables and recorded artifacts remain. Do not repeat that retirement.

All114 original parser compatibility tests and16 parser protocol controls pass
and are closed. The first compatibility supervisor timed out before admission;
a separate supervisor ran one fresh guest invocation. Batched evidence closure
also retains the original failure and the earlier no-mutation closure timeouts.
Both88-command parser performance histories remain required. The incremental
history was launched at16:13:49; repository remains unstarted pending its result.

Production Python has changed on main since the measured launcher was frozen.
Review the exact diff and merge the indirect-option path with main's current
compiler/tool routing. Do not reuse the old integration's assumption that only
an optional installer module differs. Run the full merged Python contract suite
and require coverage of both scalar/indirect forwarding and main's compiler
selection. Qualify the merged stock-compiler launch path with strict/cache
workflows, including unreachable type/borrow errors and partial-artifact
rejection. If invocation, cache identity, bytecode, limits, options or execution
behavior changes on the measured path, require a new matched end-to-end screen
before claiming that the merged launcher retains its measured performance.

Reuse completed Rust/runtime and performance results only through exact source,
binary and retained-evidence bindings. Report reused qualification separately
from fresh executions. Do not silently transplant timings to a new compiler key
or rerun unchanged histories just to obtain a better result.

After qualified integration, update the usage command and current-result table
with the full campaign, native gaps and parser limits, then push main normally.
The engine still runs selected function/test bodies; this does not add libtest,
unwinding, threads or general OS/FFI support.

Next runtime work should start with fresh owned native-PC samples on the newly
adopted VM. The current sampling launcher lacks an indirect-call option; add and
test explicit forwarding before using it. Reuse the current observation validator,
which knows indirect transitions, and fresh profiles for static instruction
identity. Historical dynamic counts changed with macOS CPU-feature detection;
never mask that difference or use entropy replay for performance measurements.

The read-only sampler review identifies three coupled changes: forward
`--jit-indirect-calls` into the owned VM invocation and record it in the plan;
validate its boolean value, command agreement and resumable-call requirement
in summarize_owned_sample.runtime_options; and require the same value in both
native maps during attribution. Preserve historical plans without that option
as disabled. Add rejection controls for missing/extra flags, nonboolean values,
incompatible modes and disagreement between the command and maps. The current
scalar-runtime-sampling attribution imports the older scalar-private-transfers
validator; use runtime-composition-workflows/native_observation.py explicitly
instead. Reuse existing attribution controls only when their source and evidence
still match. Scalar spans identify whole leaf bodies, so their samples must not
be reported as individual memory or arithmetic instructions without finer proof.
These implementation changes remain deferred until frozen qualification closes.
