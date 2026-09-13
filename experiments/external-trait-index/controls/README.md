# Native resolution controls (not yet compiled)

These ordinary Rust fixtures are intended for the separately built candidate
compiler. They do not inspect or modify any development benchmark or holdout.
They are not an executed qualification and do not establish index coverage.

Compile `external.rs` once as crate `external`, with the option off. Compile the
same physical `main.rs` against that unchanged external rlib using off/on/off
compiler options and separate incremental directories. Keep the module and
MonoItem placement options off and use the ordinary complete compiler sysroot.
Retain all child arguments, status, stdout, raw JSON diagnostics, source bytes,
binary hashes, source/tool/library guards and outer canonical lock receipts.
No diagnostic field is normalized or omitted. Preserve each failed attempt.

The successful default program prints `448`. A source edit replacing only
`use external::reexport::nested::Selected;` with
`use external::right::Select as Selected;` must print `800` with unchanged
`select` function bytes. Restore the source and require `448` again. A separate
Unicode/comment insertion before `select` must also preserve `448` while moving
subsequent actual diagnostic spans. Perform these histories independently in
each mode; do not prebuild any future source state.

The controls cover repeated present-name lookups, an external trait alias,
nested trait reexports, an associated type and constant sharing a symbol, and a
macro-created local trait which must retain the mutable-table path. Add these
configurations to the original source, always compiling both off and on before
comparing complete raw diagnostic records:

| `--cfg` | Required outcome |
| --- | --- |
| `select_right` | Successful execution, `800` |
| `missing_method` | Rejection containing E0599 |
| `ambiguous` | Rejection containing E0034 |
| `select_right` plus `unused_import` | Successful execution, `800`, with unused-import warning |
| `type_error` | Rejection containing E0308 in uncalled function |
| `borrow_error` | Rejection containing E0382 in uncalled function |
| `const_error` | Rejection containing E0080 in uncalled constant |

After every rejected state, restore the original bytes, compile and execute in
the same incremental directory, and require `448`. A failed compile cannot
serve as successful cache validation. Diagnostic order, source text, labels,
expansion information, rendered output and warnings remain part of equality.

These native fixtures cannot construct all internal `BindingKey` states. The
separate, unrun compiler unit control in `projection.rs` exercises duplicate
`(Symbol, Namespace)` projections with distinct hygiene/disambiguators, using
a helper that accepts keys independently of any declaration value.
The default-off `-Zverify-external-trait-item-index=yes` shadow comparison at every actual indexed lookup must
also match the original predicate before any timing run. The shadow work must
remain absent from performance runs. Option tracking and memory/size checks are
still required. No native runner, full compiler build, shadow result, or speedup
is supplied by these source fixtures.
