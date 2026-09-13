# Optional owned Cargo selection

`interpreter.py` and `std_mir.py` accept `--cargo-key KEY` for an independently
installed Cargo executable. The default remains `cargo +nightly-2026-09-08`.
Changing Cargo does not rebuild or change the selected exporter/VM tool key.
Cargo selection has its own project and standard-library cache identities and
is included in launcher/std command receipts.

Import a previously qualified matched build, without invoking Cargo or rustc:

```sh
python3 scripts/custom_cargo.py \
  --qualified-report /absolute/owned/worktree/.work/cargo-info-cache-build-01/summary.json \
  --mode stock
python3 scripts/custom_cargo.py \
  --qualified-report /absolute/owned/worktree/.work/cargo-info-cache-build-01/summary.json \
  --mode candidate
```

The importer verifies the selected binary, complete source manifest, compiler
and builder identities, build/test source hashes, command receipts and saved
outputs against the completed qualification. It copies the executable and
exact provenance into `.work/cargos/KEY/payload`, then makes that directory and
its files read-only. `ready.json` binds the current worktree, content identity
and file stamps. Importing from another explicitly selected owned worktree
reads that evidence without modifying or linking its files. The original
qualification and matched build profiles remain part of the imported identity.

Validation on reuse checks inode, mode, size, mtime and ctime without rehashing
the executable or running discovery subprocesses. It rejects replacement
symlinks, writable/changed installed payloads and changes to the recorded
dated compiler installation. This detects accidental local mutations; the
manifest is not authentication against someone who can rewrite the whole
installation and its records.

On macOS the importer also walks the non-system dynamic-library closure using
`otool`, including transitive dependencies and proved runpaths. It records
logical/resolved paths and full library hashes, and binds reuse to file/link
stamps plus every runpath candidate's existence. Homebrew library replacements
and alias retargeting invalidate the installation. Unresolved or ambiguous
runpaths fail import; relocation must preserve the same proved closure. Warm
validation never runs `otool`. System dyld-cache libraries are assumed stable
within the recorded `uname` platform/kernel build identity; they are not hashed
individually. Other operating systems currently fail this closure import until
equivalent validation is implemented.

The selected command begins with the absolute installed Cargo path, followed
directly by `check` or `fetch`. A standalone Cargo binary does not accept
rustup's `+toolchain` argument. The launcher explicitly sets `RUSTC` to the
pinned compiler and `RUSTUP_TOOLCHAIN` to its dated host-qualified toolchain.
With `--compiler-key`, `RUSTC` instead names that validated owned compiler and
the existing exporter/compiler association checks still apply. Cargo's build
compiler provenance and the runtime compiler selection are separate: Cargo
itself need not be rebuilt to select an owned compatible-host compiler.

Conflicting `RUSTC`, `CARGO_BUILD_RUSTC`, `CARGO`, `RUSTUP_TOOLCHAIN`,
`RUSTUP_HOME`, `RUST_SYSROOT` and loader environment overrides fail before
tool/std setup. The launcher continues to set `RUSTC_WORKSPACE_WRAPPER=''`:
that explicit empty value disables inherited Cargo configuration wrappers.
The std setup retains its existing MIR flags, features, target and profile.

For example, use the key printed by the importer with the existing exporter
key:

```sh
python3 scripts/interpreter.py --manifest-path PROJECT/Cargo.toml \
  --package PACKAGE --entry ENTRY --tool-key EXPORTER_KEY --cargo-key CARGO_KEY
python3 scripts/std_mir.py --cargo-key CARGO_KEY
```

Importer and synthetic routing tests establish selection and identity behavior.
They are not warm-build performance measurements; that requires a separate
matched Cargo A/B history with real edits and correctness controls.
