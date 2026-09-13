# Separate source-path and source-observable prerequisite

`scripts/qualify_std_source_observables.py` is a source-only, unexecuted
prerequisite implementation. It adds no command or timing adjustment to the
existing 36-command compiler integration or 27-command performance screen.
Run only after review, compiler/tool installation and both explicit v2 std
preparations, under the canonical workload lock:

```sh
python3 scripts/qualify_std_source_observables.py \
  --compiler-key "$COMPILER" --tool-key "$TOOLS" \
  --std-mir-off-key "$OFF_STD" --std-mir-on-key "$ON_STD" \
  --run-id std-source-observables-01 --lock-wait-seconds 600
```

The 57 retained child commands include six direct, unmapped E0080 histories:
native std and both prepared std identities, each through the original and a
byte-identical independent second compiler/source prefix. Each history compiles
cold, prepends a Unicode comment and two source lines, then restores the original
source and recompiles. Actual nested byte/character coordinates must move by
the exact edit, and restored structured diagnostics must match. Raw standard
snippets must already be complete and match inventoried source bytes. The
second compiler must report its own sysroot and the same real version.
The complete native and both prepared copy inventories, their hashes, and final
unchanged-byte/stamp checks are retained for independent archived validation.

Two additional disposable prepared-std copies remove or corrupt only
`core/src/panic.rs`. They must still reject the program with E0080 and fail the
raw-source validator. No installed compiler, original source snapshot, prepared
std or library is modified. Independent copies, native artifacts and all setup
work are outside any timing measurement; admission reserves their full logical
size plus 8 GiB. Existing identities are checked around commands.

Application controls cover both native and exported execution, with the mono
policy explicitly off and on and module grouping always off. A real proc macro
returns its input token's `file`, `local_file`, `line`, and `column`; two functions
also expose `file!()`, including an owned `src/core/src/panic.rs` application file.
An explicit Cargo library target shares `src/main.rs` with the direct native
entrypoint; Cargo automatic binaries are disabled for this fixture.
Each route executes unmapped, with verified std-only diagnostic mappings, with
an extra application `src` mapping, then restored. Same-width comment changes
cause selected recompilation while preserving observed source coordinates.
Actual native compiler command receipts and exporter NUL argv records prove the
selected policy and exact ordered remap flags. Native and bytecode artifact
snapshots are retained alongside actual program output.

The std-only mapping must leave every same-route application observable
unchanged. The separate application-map sensitivity control must change only
`Span::file()`: pinned `rustc_expand::proc_macro_server::span_file` uses
`prefer_remapped_unconditionally`, whereas `file!()` observes MACRO scope and
`local_file()` retains the local path. This is deliberately not a claim that
diagnostic-only remapping is invisible to all proc macros. Source-relative
identities and exact coordinates agree across native/exported routes. Both
compile the original application source tree: the launcher's `workspace_path`
is an artifact cache, not a source copy. Raw paths remain in the records. The
archived validator binds the actual launch's compiler/tool/std/artifact identity
and recorder directory, source cwd and command index. No diagnostic
string or snippet is substituted, normalized to fake equality, or reconstructed
as compiler output. These mappings remain confined to correctness qualification.

The producer self-checks its result with the pure archived validator
`std_source_observables.validate_source_observables(path, owner, compiler_key,
tool_key, stds, compiler_sysroot=..., read_bytes=...)`. Its checked return has
`path`, `sha256`, `result`, and an absolute-path `evidence_files` hash map. The
screen should freeze it as `plan.source_observables`; the saved assessor must
require the same checked prerequisite. A missing, old, failed, mismatched or
incomplete prerequisite cannot be inferred from the separate 36-command result.

Six focused compiler-free contracts are prepared but unrun. Actual source-path,
native, proc-macro, VM and restored-artifact checks have not been executed.
