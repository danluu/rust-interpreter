# Owned stage2 compiler experiments

The optional custom compiler path uses one installed compiler and one matching
exporter/wrapper/VM toolset for both stable-CGU policies. This is a new matched
custom-compiler baseline; it is not interchangeable with an earlier stock
compiler measurement. Stock launcher defaults and legacy tool keys are unchanged.

Prepare a complete stage2 installation prefix containing matching `rustc`,
native standard libraries, `rustc-dev`, `rust-src`, and compiler support tools.
On Darwin, normal stripping also requires an executable
`lib/rustlib/HOST/bin/rust-objcopy` from the compiler's LLVM distribution; a
bootstrap configured with `llvm-tools = false` can omit it. Include that tool in
the package inventory and provenance. Use the compiler's
distribution components: bootstrap may put compiler-private libraries in the
build compiler's sysroot rather than its resulting stage2 sysroot. Never copy
arbitrary stage1 private libraries into stage2. The prefix must not include Cargo
or live source-directory symlinks. Its macOS dylibs and loader paths must resolve
within the installation or system libraries.

The provenance JSON requires `stage: 2`, the 40-character `source_commit`, and
64-character `patch_sha256`, `bootstrap_sha256`, and `build_receipt_sha256`.
Additional provenance fields are retained. Install with:

```sh
python3 scripts/custom_compiler.py --install-from /owned/packaged-stage2 --provenance /owned/provenance.json
python3 scripts/build_custom_tools.py --compiler-key COMPILER_KEY --run-id custom-tools-01
```

Installation copies and freezes the complete prefix under
`.work/compilers/COMPILER_KEY/sysroot`; it does not modify rustup. The key hashes
the file inventory, compiler version, and build provenance. Warm validation checks
the complete inventory and ctime-inclusive file stamps against the publication
receipt. Tool setup uses two jobs and records Cargo's actual executable, hash,
verbose version, build settings, source hashes, compiler identity, and binary
hashes. It retains build output and an exact child-process receipt. Both setup
commands acquire the shared benchmark lock and require 8 GiB free.

Run the ordinary launcher with `--tool-key TOOL_KEY --compiler-key COMPILER_KEY`
and `--stable-cgu-partitioning off` or `on`, retaining all other workflow options.
The custom path requires preinstalled matching tools. The wrapper supplies the
explicit compiler policy to native host and guest jobs; Cargo target Rustflags
alone do not reach host jobs when an explicit guest target is selected. Conflicting
compiler/sysroot/policy settings and response files fail before compilation.

Compiler identity and policy separate project and std-MIR namespaces. Std setup
uses the same custom compiler and the existing metadata-only flags; the stable-CGU
flag is deliberately not added to std preparation. Its two namespaces contain
separately prepared metadata under the same flags. Native std build helpers also
retain the compiler's default grouping policy. The measured project commands
apply the selected policy to their native helpers and dependencies.

Compiler validation, std readiness, Cargo, export validation, and execution remain
inside their ordinary launcher boundaries. A same-toolset off/on screen still
needs a frozen plan, independent caches, actual edits, and correctness controls;
installing these tools makes no performance claim.

Before a workload comparison, qualify the real installed pair in the same
checkout where it will run:

```sh
python3 scripts/qualify_custom_compiler.py --compiler-key COMPILER_KEY --tool-key TOOL_KEY --run-id custom-integration-01
```

The harness requires the tool build's Rust sources and Cargo identity to match,
prepares and verifies both std-MIR namespaces, and runs 22 complete launcher
commands on a fresh local path-only workspace. It checks shared native/guest
dependencies, a native build script and proc macro, changed computed values,
16 expected uncalled-error rejections, and compiled restoration. Cargo verbose
receipts establish the actual compiler paths and host/guest roles. Passing
off/on bytecode must agree; restored bytecode must match the original. All
commands, outputs, selected bytecode, and failed runs are retained under the
explicit run ID. This tests correctness; its small fixture and times are not
performance evidence or a holdout. The caller must configure this checkout's
`.work/benchmark.lock` to the campaign's shared lock before admitting work.

The same source history also runs 11 native Cargo commands with the ordinary
pinned public compiler and a separate target directory. Actual native output
must agree with the VM results. The eight public uncalled-error rejections must
match both custom modes' structured core diagnostics, including spans and
children; only rendering and owned checkout path prefixes are normalized.
The fixture's explicit two-CGU development and build-helper settings are the
same for all arms and exist to exercise the merge branch. They do not alter any
workload comparison profile.
