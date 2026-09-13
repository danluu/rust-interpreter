# Native host library O1 experiment

Status: source-only, unqualified and untimed. No performance claim.

`--host-library-opt=on` selects O1 code generation for unselected native Cargo
`lib`/`rlib` units under the launcher's explicit-target `--std-mir` route. It
requires one ordinary source input, a single library crate type and an ordinary
linked output. This includes libraries shared by proc macros and build scripts;
it does not infer macro-only ancestry or choose dependency names. Proc-macro
dylibs, build-script executables, selected exports, guest units, metadata-only
units and probes retain their existing arguments.

The policy shares the existing proc-macro optimization parser and default-check
logic. For supported original O0 invocations it appends `-Copt-level=1
-Zmir-opt-level=1 -Clto=off`, retaining effective debug assertions and overflow
checks and therefore the original UB-check default. Explicit checks remain in
order. Explicit optimization/LTO, unstable flags (including explicit UB-check
overrides), unknown eligible options, ambiguous roles and response files are
rejected. Source cfgs, features, panic policy, debuginfo, codegen units, Cargo and
backend jobs, and ordinary checking are unchanged. No unchecked analysis or
proc-macro result is reused.

Cargo profiles are unchanged. In the pinned Cargo, `src/compiler/custom_build.rs`
derives `OPT_LEVEL` and `DEBUG` for build-script execution from the package's
profile. The wrapper changes only compiler arguments, so these inputs and all
build-script executions are retained. Std-MIR preparation occurs before the
application policy environment is set and shares the original std installation.
Function-cache `auto` remains available after ordinary analysis.

O1 has ordinary code-generation effects beyond its MIR level: lifetime markers
remain, and nonincremental host libraries may gain cross-crate-inline inference
(`rustc_mir_transform/src/cross_crate_inline.rs:79`). Native IR, debug information
and code layout can differ. Unlike proc-macro crates, these libraries also
export MIR, which may reflect those code-generation choices. Normal O1 does not
promise identical metadata or native bytes. Faster cached macro dependencies
may be offset by compiling edited host libraries at O1; cold cost can increase.

Omission and explicit `off` retain old tool/workspace behavior. `on` requires
`host-library-opt-v1` on the exact exporter and a publication-time probe of the
actual adjacent wrapper, including its compiled sysroot. The wrapper checks the
physical compiler executable before invoking it. Enabled project caches use a
separate policy namespace. Current custom compiler/Cargo, frontend workers,
proc-macro optimization, stable partition and borrowck policies cannot combine
with this option. Guest and host dependency caches are therefore not reused
across the enabled/default policy transition.

Focused Rust routing and mocked launcher/publication controls are prepared in
`crates/mir-export/tests/host_library.rs` and
`tests/test_host_library_launcher.py`; none has run for this source-only change.
Before timing, qualify the unchanged proc-macro parser controls plus native
checks, actual macro/build-script outputs, cold/edit/restore exports, and compiler
argv for host/guest roles. The shared publisher's explicit host-library handoff
is prepared in [PUBLICATION.md](../experiments/host-library-opt/PUBLICATION.md).
Its recorded wrapper binder is also used by the existing automatic publisher.
No host-library performance screen has been implemented.

## Prepared real controls

`tests/test_host_library_native.py` reuses the existing proc-macro fixture,
command logger, strict diagnostic comparison and Cargo/std/VM workflow without
changing the original macro tests. Its three histories cover:

- Pinned native, wrapper off and wrapper on compilation of uncalled type,
  borrow, const-evaluation and unconditional-panic errors with source-position
  changes and a valid restoration after each rejection. Full structured
  diagnostics retain spans and snippets; only rendered text is ignored.
- Native libraries consumed by an ordinary native executable, checking default
  and explicit debug/overflow combinations, `cfg(ub_checks)` without invoking
  undefined behavior, generic/inline calls and observable drop effects.
- The shared library used by both an actual proc macro and a native build
  script, with macro-body, shared-library, declared-file-input and source-position
  edits, a generated type error, then exact restoration. Every valid state runs
  public native tests and off/on bytecode. Off/on bytecode must match, edits must
  change it, and restoration must match the original bytes. Source snapshots,
  bytecode histories and commands remain in the owned fixture directory.

The last history uses function-cache `auto` after ordinary analysis. Both build
scripts retain `OPT_LEVEL=0`/`DEBUG=true`; the selected test checks the actual
shared-library value from the native build script. Proc-macro call-site file,
line and column become constants checked by both native and interpreted tests.
Cold Cargo records must include a host shared library, guest shared library,
proc-macro dylib, build-script executable and selected export. Every actual
compile is matched by PID to the existing final compiler-argv recorder. The
complete forwarded argv must equal the original plus existing std/MIR routing
and, only for eligible on-arm libraries, the explicit O1/check-preserving flags.
The same final-argv check covers successful and failed direct library compiles.

No history has run yet. After a caller acquires the canonical workload lock and
freezes one supporting public exporter/wrapper/VM plus a complete prepared std
sysroot, the focused commands are:

```sh
cargo +nightly-2026-09-08 test --release --locked --offline --jobs 2 -p rust-interp-mir-export --test host_library --test host_proc_macro --test wrapper_route
python3 -B -m unittest discover -s tests -p test_host_library_launcher.py -v
python3 -B -m unittest discover -s tests -p test_host_library_native.py -v
```

The final command requires `RUST_INTERP_TEST_EXPORTER`,
`RUST_INTERP_TEST_WRAPPER`, `RUST_INTERP_TEST_VM`,
`RUST_INTERP_TEST_STD_SYSROOT` and an owned `RUST_INTERP_TEST_ARTIFACT_DIR`.
`RUST_INTERP_TEST_RUSTC` may name the exact public compiler explicitly. These
are correctness controls, not timings. The prepared shared publication policy
binds their frozen inputs and actual receipts to the final tool key; standalone
execution without that binding does not qualify a toolset for a later screen.
