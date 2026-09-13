# Borrow-check query reuse correctness fixtures

These fixtures exercise the real compiler through an externally supplied exporter.
They do not collect build or runtime performance measurements and do not modify
Nushell or any other checkout.

Run `tests/test_borrowck_cache.py` with `RUST_INTERP_TEST_EXPORTER` set to the
exporter executable. `RUST_INTERP_TEST_RUSTC` can override the pinned real rustc.
`RUST_INTERP_TEST_VM` optionally executes the exported test bytecode as well;
the export is always compared against the full-export control with reuse off.
`RUST_INTERP_TEST_ARTIFACT_DIR` optionally retains each case's sources, compiler
outputs and `commands.jsonl` receipts in a newly created child directory.

The caller must arrange the repository's shared correctness/benchmark lock before
running these compiler tests. The script does not acquire another lock itself.
Without `RUST_INTERP_TEST_EXPORTER`, normal unittest discovery skips the class.

`basic.rs` covers changed bodies, untouched functions and a concrete-to-opaque
return transition. The two-crate fixture keeps the consumer source unchanged
while editing its dependency's function body, constant, macro, public type or
trait implementation. Native rustc controls check successful output and rejected
programs. Additional cases check uncalled errors, diagnostics and lint
expectations (including borrow-checker `unused_mut` diagnostics), compilation
without incrementality, explicit MIR/NLL-fact dumping, nondefault Polonius,
internal compiler attributes,
preservation of requested compiler diagnostic output, and metadata-only MIR encoding.
The ordinary body-edit cases assert that rustc reloads unchanged optimized MIR
without calling its borrow-check provider. `newly_reachable.rs` first leaves
private functions uncalled, then edits the caller to use them: their checks were
already green, but optimized MIR was not previously needed. This requires actual
empty-result reuse and nonempty opaque-result fallback at ordinary optimization.
Every revision in this case also enables rustc's incremental hash verification.
`test_export.rs` exercises the actual selected-test exporter at ordinary MIR
optimization and fixed `-Zmir-opt-level=3`. The latter enables MIR inlining even
with incrementality, so a changed callee invalidates unchanged callers' optimized
MIR and requires green borrow-check values during rebuilding. Warnings and lint
expectations must survive these paths. These are correctness qualifications;
they do not establish a performance benefit on any workload. Only rendering is
ignored in comparisons; source spans, labels, suggestions and child diagnostics
must agree with the controls.
