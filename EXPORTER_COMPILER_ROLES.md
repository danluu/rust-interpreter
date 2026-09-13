# Explicit exporter compiler roles

This source-only option separates the compiler that builds the exporter from
the compiler frontend embedded in it. It has not yet been built, linked, or
qualified. No publisher or installed-tool validator accepts a new composition
policy in this change.

With `RUST_INTERP_COMPILER_ROLES` absent, the original build script probes
`RUSTC`, uses its sysroot for the exporter default and linker rpath, and reports
its commit in the existing capabilities. Existing capability JSON is unchanged.
The wrapper's new `--rust-interp-compiler-roles` probe prints `null` in this mode.

The opt-in is an absolute path to a JSON binding with these required fields:

```text
schema_version: 1
policy: "separate-compiler-roles-v1"
build:
  executable: {path: D/bin/rustc, sha256: actual build-compiler SHA}
  verbose_version: exact stdout from D/bin/rustc -vV
  default_sysroot: D
runtime:
  executable: {path: E/bin/rustc, sha256: actual runtime-compiler SHA}
  verbose_version: exact stdout from E/bin/rustc -vV
  default_sysroot: E
runtime_source_commit: actual commit-hash reported by E/bin/rustc
runtime_driver: {path: E/lib/librustc_driver-HASH.dylib, sha256: actual SHA}
private_sysroot_manifest: {path: absolute JSON path, sha256: actual SHA}
build_rustflags: ["--sysroot=B", ... exact remaining encoded Cargo flags]
```

The independently hashed private-sysroot manifest contains:

```text
schema_version: 1
build_compiler_sha256: actual D/bin/rustc SHA
runtime_source_commit: actual runtime source commit
sysroot: B
host: host reported by both compilers
files: {relative ordinary file path: SHA-256, ... every file under B}
```

`D`, `B`, and `E` are canonical absolute paths; `B` differs from both compiler
default sysroots. `B` need not contain a compiler executable. For a stage0-built
stage1 frontend, `B` contains the genuine beta standard-library inputs and the
entire successful native compiler-build stamp closure, including non-rustc
dependencies and host proc-macro artifacts. It must not contain stage1's
application standard library or a mixture of check and build outputs. The
build script hashes and compares every ordinary file under `B`; symlinks,
unlisted files, missing files, and different bytes fail. It also requires
separate rustc_driver metadata, beta std metadata (possibly inside its rlib),
and the exact runtime driver bytes at their private link location. Assembling
that inventory from actual successful build/archive provenance remains the
compositor's responsibility; a supplied inventory alone is not qualification.

The build compiler is exactly the named `RUSTC`. Both actual compiler binaries
are hashed and invoked with `-vV` and `--print sysroot`; their outputs must
match the binding. Their commits may differ. `HOST` and `TARGET` must both
match the actual host tuple. `CARGO_ENCODED_RUSTFLAGS` must exactly equal the
bound flags, with one `--sysroot=B`. There is no added optimization setting or
mandatory `prefer-dynamic`. LLVM native link-search flags, if needed, are
explicit bound inputs. Version overrides, response files, alternate
`RUSTFLAGS`, and compiler wrappers are rejected, including empty overrides.
The caller must still freeze Cargo/configuration inputs and retain actual
rustc command lines: a build script cannot prove all flags Cargo will append.

The exporter rpath points to `E/lib`, and its compiled default application
sysroot and commit come from the actual runtime probe. Explicit application
`--sysroot` arguments, including a prepared source/MIR sysroot, retain their
existing behavior. The beta build sysroot is never substituted for an
application sysroot. Selected Cargo exports must name `E/bin/rustc`.

At exporter startup, the opt-in checks the runtime compiler and driver file
identities recorded after build-time byte verification. These are full Unix
device/inode/mode/size/mtime/ctime tuples, checked with no symlink following;
this adds no compiler subprocess or complete driver hash to each invocation.
It compares `rustc_interface::util::rustc_version_str()` with the actual
runtime version header and uses `dladdr(rustc_driver::run_compiler)` to require
the expected loaded driver path. A different driver selected through loader
environment variables fails, even if it reports the same version. Current
support is macOS/Linux. Loader discovery and ABI compatibility still need an
actual build and run. The std-only wrapper checks file identities without
loading the frontend; the exporter performs the loaded-image/version checks.

The exporter adds the complete validated binding as `compiler_roles` in its
normal capability JSON. The wrapper's new probe returns the same JSON. The
separate manifest hash, actual build/runtime executable hashes and versions,
runtime driver hash, and exact encoded flags therefore remain distinguishable.
The existing worker and host-library compiler commit fields refer to the
runtime frontend. Moving or replacing bound runtime files requires rebuilding
the exporter with a new binding; this change does not relabel old binaries.

Eight pure Rust controls are defined in
`crates/mir-export/tests/compiler_roles.rs`. They cover crossed build/runtime
identities, actual probe output substitution, environment overrides, private
sysroot selection, exhaustive file tampering, strict schema/hash checks,
default behavior and loaded-image/identity rejection, and Cargo routing to
the runtime compiler. All eight passed in the default-mode qualification. The merged
source `56e9aea9` subsequently passed all 548 release workspace tests (10
ignored, none failed or filtered), including all eight role controls and four
getcwd controls, plus both getcwd native tests and their 33 child commands.
The actual exporter retained its default capabilities and the wrapper's role
probe returned exactly `null` followed by a newline.
[Merged qualification evidence](results/exporter-roles-getcwd-qualification-01/README.md).
These checks do not establish private metadata/linker compatibility or actual
split-role dylib discovery.

The next bounded qualification must assemble `B` from verified beta payloads
and the full successful native rustc build stamp, freeze both role bindings
and all loader inputs, and build with the actual beta compiler. It must retain
actual compiler argv, binary dependencies/rpaths and loaded libraries, probe
the resulting exporter and wrapper, and exercise native/exported diagnostics,
application sysroots and the selected compiler feature. Ordinary Rust
metadata-version/SVH checks and the production anti-spoof guard stay enabled.

A later publisher needs a distinct composition kind with independent build
compiler/private closure and runtime compiler/driver/loader identities. Its
tool key must derive from actual binaries and those inputs. Existing
`build_custom_tools.py`, `custom_compiler.py`, public-tool publication and
qualification schemas remain unchanged; their existing stage2/same-compiler
contract must not be used to describe this unqualified composition.
