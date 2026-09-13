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
argv for host/guest roles. Use the existing shared publisher later; its host
library capability hook is `host_library_opt.bind_wrapper_capability`. No new
publication or performance harness is introduced here.
