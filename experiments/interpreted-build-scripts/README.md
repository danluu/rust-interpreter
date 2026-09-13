# Interpreted Cargo build scripts: source qualification fixture

This checkpoint contains a generic fixture and an implementation contract. No
Cargo/VM support is added, and no fixture compilation, test or measurement has
run. The local-only lockfile is source-prepared and still needs Cargo validation.
The first execution must be an ordinary pinned native Cargo baseline. There is
no speedup or coverage claim and no change to an application or its build script.

The objective is to avoid LLVM/object generation for a Rust library whose host
use is confined to interpreted build scripts. Frontend expansion, resolution,
type/borrow checking, const evaluation and required MIR checks remain. A library
also needed by a native proc macro must still provide native code. This can
address a build-script-induced native host compilation, but neither eligibility
nor replacement export/runtime cost for any large project is established here.

## Fixture and two dependency cases

`fixture` is an independent Cargo workspace containing only local dependencies:

* `ibs-fixture-app` uses `ibs-fixture-helper` as both a normal dependency and a
  build dependency. Its build script reads the actual `IBS_FIXTURE_SEED` and
  `input.txt`, calls the helper, writes generated Rust and emits Cargo directives.
* `ibs-fixture-macros` is always a real native proc macro. By default it does not
  depend on the helper. The helper's host use is then build-script-only; its
  separate normal target use still exists.
* App feature `native-shared-helper` adds that same helper as a dependency of
  the native proc macro. A future engine must build a separate native helper
  artifact or retain the native route. Giving that proc macro metadata-only
  input is incorrect. The macro invokes the helper to construct its expansion,
  and an unchanged application assertion compares that value with the current
  runtime helper, including after a helper edit.

The three app tests check generated-file contents, real emitted cfg/env values,
and macro output. Expected results are calculated from the current helper and
inputs; the runner must not supply expected build-script output in place of
executing the script. `history.txt` records one line per actual script run.
`context.txt` binds Cargo's actual OUT_DIR, cwd, host/target, profile and job count.
The fixture uses both `cargo:` and `cargo::` directives, with observable ordering.
Sources and assertions remain the same between native and future custom arms.

`unsupported-build-operation` deliberately writes `before-unsupported.txt`
before spawning the actual Cargo-provided `RUSTC --version`. Native execution
must succeed and retain that marker plus the child's actual stdout. Subprocesses
are outside the first proposed interpreter policy: its strict qualification
mode must reject the whole execution graph before entering main, so neither
marker nor any other script effect occurs. This cannot be implemented by a
runtime trap after the write. A later policy supporting subprocesses would need
a separately frozen unsupported-boundary control.

The four files under `fixture/controls` are uncompiled insertion fragments, not
workspace targets. A qualification controller replaces the unique
`// QUALIFICATION_ERROR_SLOT` in either `app/build.rs` or `helper/src/lib.rs`
with one fragment at a time. They exercise uncalled type/borrow failures,
constant evaluation and unconditional-panic checking. Restore the exact saved
bytes after every case; never alter tests to accept an error or stale output.

## Cargo and compiler contract

The pinned Cargo source already has a host execution hook:
`src/compiler/compilation.rs::Compilation::host_process` uses an explicit
`host.runner` under the unstable host configuration with
`target-applies-to-host=false`. This supplies a runner with the real build-script
artifact path. It does not change artifact production or remove native codegen.
`src/compiler/custom_build.rs::build_work` must retain responsibility for cwd,
OUT_DIR, HOST/TARGET, feature/cfg variables, DEP metadata, jobserver inheritance,
stream capture, directive parsing, execution failure and rerun dependencies.

Current Cargo requests link outputs for host Build units, waits for upstream
objects for executable consumers, and passes linkable externs to build scripts.
The relevant boundaries are `unit_dependencies.rs::check_or_build_mode`,
`build_runner/mod.rs::only_requires_rmeta`, and `compiler/mod.rs` emission/extern
selection. The repository wrapper deliberately leaves host units native;
the exporter currently requires metadata-only emission.

A future implementation needs an explicit interpreted-host compilation policy:

1. Cargo constructs and fingerprints distinct interpreted-host units and actual
   metadata/MIR/program outputs. Preserve its feature resolver, profile, host
   cfg, build dependencies and script-run units. The target app's ordinary
   dependency and a native proc macro's dependency are not automatically the
   same compilation unit. Do not infer roles from package names or from the
   absence of `--target` alone.
2. Fully checked host libraries emit genuine `.rmeta` containing required MIR.
   Use a complete host-compatible standard MIR sysroot from the exact compiler.
   Native proc-macro dylibs and their transitive native closure keep native
   artifacts/sysroot. Do not mix compiler metadata identities or replace an
   expected `.rlib` with renamed metadata, an empty file or a success sentinel.
3. The build-script exporter produces a real program artifact after normal
   checking, with complete dependency and source/flag identities. Cargo knows
   that artifact's type and the required runner. A genuine compiler bytecode
   backend could offer another implementation; none exists in this checkpoint.
4. Cargo fingerprints the selected compiler/exporter/VM/policy/runtime/sysroot
   identities and artifact paths; changing mode cannot reuse a native unit as an
   interpreted unit. Normal dep-info and rerun-if-changed/env-changed decisions
   remain authoritative. Do not run a script during export or cache its effects
   outside Cargo's established build-script freshness machinery.
5. Every interpreter support decision is complete before execution. Strict
   qualification rejects unsupported programs. An eventual automatic fallback
   may select native compilation before any script side effect, but must never
   restart native execution after a partial interpreted run. A compilation
   error is never a reason to bypass checking through fallback.

Merely adding `host.runner` while still compiling native dependencies cannot
save their codegen cost. Producing valid metadata and honestly changing the
consumer/output contract is necessary. Preserving link/codegen-induced validity
checks also needs qualification; metadata-only analysis is not assumed to cover
every native diagnostic automatically.

## Runtime contract still to implement

The VM currently supports immutable environment reads, checked allocation/TLS,
randomness and a CPU-query shim. Guest filesystem, stream I/O and subprocesses
are absent. Its artifact loader's own file accesses are not guest I/O, and its
CLI prints an entry's numeric result, which must not pollute Cargo's stdout.

The first useful implementation must preserve real main-entry/termination and
flush/drop behavior, actual process input/cwd, checked file and fd operations,
errno/partial-write errors, and unmodified stdout/stderr bytes. No canned
`cargo::` messages, generated-file substitution or mocked environment is allowed.
Buffer operations must translate checked guest memory; tagged guest pointers
cannot be passed directly to arbitrary native libraries. General subprocesses,
environment mutation/enumeration, unwind/catch behavior, foreign globals and
arbitrary FFI remain separate unsupported boundaries until implemented and
qualified. A `println!` or file call being type-correct does not prove its whole
standard-library call graph is supported. Native proc-macro execution remains
part of every compilation that requires it.

## Planned first native baseline

No executable runner or admission plan is provided yet. Before running, freeze
this whole fixture, controller source, actual public Cargo/rustc hashes and
versions, compiler closure, manifest/config discovery, full commands/environment
and original source bytes in a fresh owned run directory. Use existing owned
supervision/process receipts and the canonical absolute workload lock
`/Users/danluu/dev/rust-interp/.work/benchmark.lock`, bounded600-second admission
and two Cargo workers. Retain complete raw streams and every failure.

Copy the fixture into the owned run directory. Use the installed pinned public
Cargo and rustc from `nightly-2026-09-08`, the ordinary native std, and an explicit
`--target aarch64-apple-darwin` so host and target roles are observable. Clear
inherited RUSTFLAGS/encoded flags, rustc/workspace wrappers, RUSTDOCFLAGS/encoded
doc flags, Cargo build/profile/target overrides and interpreter variables;
record the resulting environment and reject unbound Cargo configuration. Keep
fixture-default features/profile and default libtest concurrency. Set
`RUSTC` to that exact public compiler and `CARGO_TARGET_DIR` to the owned target.
The baseline command template is:

```text
<pinned-cargo> test --manifest-path <owned-fixture>/Cargo.toml
  --package ibs-fixture-app --lib --target aarch64-apple-darwin
  --locked --offline --jobs 2 --message-format=json
```

The baseline has28 planned Cargo commands, with distinct targets for the three
groups below. All are correctness controls, not performance samples.

* Default dependency case,8 commands in one target: original (seed absent),
  unchanged original, helper `input * 3 + seed` to `input * 5 + seed`, input11
  to17, seed4, exact source/input restoration with seed absent, wrong generated
  value (`transform(input, seed) + 1` in build.rs), then restoration. The wrong
  case must compile but fail the generated-value test; all others pass3 tests.
  The unchanged command must leave build-script history/files unchanged. Source,
  helper, input and environment changes must trigger the appropriate Cargo work.
* Uncalled failures,16 commands in that same default target after restoration:
  for each of the four fragments, insert into build.rs, expect compile failure,
  restore and pass; then repeat insertion/restoration in helper/src/lib.rs.
  No failing compilation may execute the script or tests. Retain old successful
  artifacts, but prove they were not executed as fresh output.
* Native shared-helper case,3 commands in a fresh target, adding
  `--features native-shared-helper`: original, helper multiplier3 to5, restore.
  All3 tests pass each time. Capture actual native macro loading and the helper
  artifact used by its native linker; test output alone is insufficient.
* Unsupported case,1 command in another fresh target, adding
  `--features unsupported-build-operation`: all3 native tests pass, with one
  actual script execution and one rustc-version child. Record that nested child,
  exact stdout and both marker files. Restore all source and feature selection.

Record the exact three test names and native outcomes, all Cargo JSON/diagnostic
records, actual compiler argv, script output paths, context/history/generated
files and their hashes. The controller must derive OUT_DIR/artifact paths from
Cargo records, not search for whichever artifact makes assertions pass. Keep
profile/job/cfg/env values and full raw path text; compare path-dependent fields
against each arm's exact known directories rather than stripping them globally.

## Future custom qualification, before large-project use

Repeat the frozen histories using the same fixture/assertions and actual custom
tools. Bind real compiler routes and expected output kinds: default script-only
host helper emits MIR metadata without LLVM objects; the shared-helper native
closure still emits and links native code. Keep the normal target role explicit
(native in the first integration control; interpreted target execution is a
separate later composition). No placeholder native artifact counts as evidence.

The strict unsupported case differs intentionally: the candidate fails support
preflight before script execution, creates neither marker, produces no Cargo
directives and runs no test. The preceding native command establishes what the
ordinary program actually does. This is an explicit unsupported-policy result,
not an equivalence pass. Every supported case must preserve generated bytes,
directives/order, cfg/env propagation, rerun decisions and test outcomes. Compare
full core compiler diagnostics for the same source histories, retaining raw
records, multiplicity and ordinary owned-path mapping only.

Only after these controls, support coverage and exact artifact contracts pass
should an unchanged exposed application's build scripts be attempted. Any later
whole-command benchmark includes all normal Cargo/compiler/export/runtime work
and cache validity checks. This source fixture makes no half-second promise.
