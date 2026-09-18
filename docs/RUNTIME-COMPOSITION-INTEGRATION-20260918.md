# Prospective runtime integration

This is an integration plan, not an adoption decision. The candidate is tool
45a1529e / VMfd21a46f. It combines native indirect transitions, checked readonly
scalar leaves and successor-only spilling on the adopted scratch/scalar runtime.
The full token and folded histories pass; the remaining guards are still pending.

Before integration require all five complete project histories (726 commands),
all114 original parser tests and both88-command edited-parser guards. Preserve
every failed setup, host-feature diagnostic and audit-lock timeout. Audit-only
checkpoint recovery never supplies a new performance pair. The final closure
must have both `all_five_gates_passed` in its summary and `candidate_qualified`
in its closure; a passing project history alone is insufficient if a parser
guard fails. Keep the current main runtime on any failed gate.

Only after closing those results, freeze a current-main integration revision.
Preserve the other session's compiler-selection, standard-library setup, Cargo
and benchmark work. The last inspected main was a92c0942; fetch again when
integration is actually admitted. Never force-push or overwrite peer changes.

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
