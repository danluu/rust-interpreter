# Prospective direct panic and scalar-store qualification

This is a new fixture and qualification proposal, prepared before any build,
native execution, export, VM execution or MIR dump of this fixture. Root review
must precede freezing/executing its controls. No performance sample is involved.
The compiler comparison remains published baseline eb91912d against candidate5
14af97a3, with the exact same selected baseline VM and wrapper.

The original `tests/panic_store_fixture.rs`, all original panic90 controls and
outputs, and `local-export-panic-coverage-failure.json` remain untouched. The
original 90 commands passed their behavioral/bytecode comparisons, but did not
exercise the planned structural case: the assignment became Copy(size8), and
Arguments::from_str separated it from the recognized panic terminator. This is
a failed coverage check, not evidence of a compiler regression or a passing
late-panic test. Its failure receipt and all its proof bindings are mandatory
inputs to this separate qualification. Do not relabel or finalize that run.

The new source is `tests/panic_store_late_fixture.rs`. It retains edition2024,
the pinned nightly2026-09-08 and default MIR optimization settings. It explicitly
opts into the pinned `panic_internals` API, with internal-feature warnings
allowed. The helper executes `*destination = !value` and directly calls
`core::panicking::panic("panic-store late fixture")`. The ordinary helper stores
the same complement and returns. Destination starts at the original value, so
a missing store cannot accidentally satisfy any complement oracle.

The installed pinned library source establishes the API premise:

- `library/core/src/lib.rs` publicly declares the panicking module.
- `library/core/src/panicking.rs` marks its API `panic_internals` and defines
  `pub const fn panic(expr: &'static str) -> !`, with the panic lang item and
  track_caller. It is a direct, non-generic function in the core crate whose
  return type is never and whose definition name is core::panicking::panic.
- The frozen exporter classifier accepts this core crate/name/never-return
  family. Formatting construction occurs inside the callee's library body,
  after its call boundary. It is not source-level argument evaluation between
  the helper's dereference assignment and direct call.

Bind both exact installed library source files and their SHA-256 hashes to the
new source manifest, alongside the candidate/baseline classifier source. This
does not itself prove the emitted MIR or instruction sequence. Actual dump and
artifact inspection must still establish that the same reachable MIR block
contains the dereference assignment and recognized original FnDef, that this
assignment is not panic_preparation, and that argument-derived size8 Store
executes before the identified panic Trap.

The expected stored value is now explicitly **the 64-bit bitwise complement of
the second argument**, not that argument unchanged. This is a prospective
semantic change to the fixture, not a relaxation of Store or same-block
coverage. Native `observe` initializes destination to the original value,
catches unwind, and independently asserts `destination == u64::MAX - value`.
The controller's decimal oracle must use `18446744073709551615 - int(value)`.
The fixed four input/output mappings are:

| Input | Normal/observed output |
| --- | --- |
| 0 | 18446744073709551615 |
| 1 | 18446744073709551614 |
| 9223372036854775808 | 9223372036854775807 |
| 18446744073709551615 | 0 |

Proposed control adaptation is a narrow copy of the reviewed original panic90
controller into new `local_export_panic_late_qualification.py` and matching
`local-export-panic-late-*` inputs/frozen/attempt/passed names. Use a fresh
`.work/runs/local-export-panic-late-20260912-01` directory, the new absolute
fixture path and crate name `panic_store_late_fixture`. Preserve the exact
90-command design: two builds; twelve native runs; eight baseline/candidate ×
inline-off/on × primary/diagnostic exports; four validated Program inspections;
64 primary VM runs covering both engines, modes and all four inputs.

Keep the original strict compiler flags, instruction/memory bounds, complete
artifact/error parity, original shared-lock ownership, fresh targets, frozen
tools/controls, and actual-core prerequisite. Both successful native modes and
successful VM modes must match the new complement oracle. Uncaught native mode
still exits101 with the new fixture panic marker; VM failure remains exit1 with
exact baseline/candidate and engine parity. Diagnostic export adds only the
same bounded MIR dump flags and must reproduce primary bytes exactly.

The new inspection schema must say `stored_value_is_complement_of_second_argument`
and `value_is_complement_of_value_argument`, and retain actual Unary(Not,bits64)
plus size8 Store provenance. Trace the helper's second argument through the
unary result into the Store source register, and its first argument into the
Store address. Establish every relevant control edge and exclude the caller's
initialization or unrelated frame stores. The actual recognized definition and
location must bind the witness Trap and actual VM panic errors. The original
same-basic-block, non-preparation, reachable-path, Store-size and exact-opcode
checks remain mandatory. If the new actual code lacks that case, preserve a
second failed coverage result; do not silently accept Copy or separate blocks.

A final new PASS would qualify only this complementary-value case and would
retain the original failed receipt as provenance. Before adoption inputs are
frozen, explicitly revise the prospective adoption prerequisite to require the
new final structural PASS plus the original failure, preserve the old adoption
draft, and re-review/refreeze its control hashes. No existing frozen core,
original panic or diagnostic receipt is modified. This document and fixture do
not claim successful compilation, execution or coverage; those remain pending.
