# In-place HIR stage2 package continuation — unexecuted

This is a source-only draft. The current ReadyHit native history at compiler
`3d7ad8282c5695196f4a4dcfd0bdceacac3f79b9` **failed** its first capture assertion.
It cannot satisfy this driver's prerequisite. No plan has been materialized and
no stage2 command has run. A reviewed new native-success source/history/archive
binding is required before admitting this continuation. This draft does not
reinterpret that failure or invent a passing prerequisite.

The scope is an already prepared, natively qualified owned compiler checkout:
ordinary in-place stage2 bootstrap, complete stage2 correctness, distribution,
and first-production packaging. `production-driver.py`, its fresh36GiB recipe,
all old source/check histories and SOURCE ownership are unchanged. The source
checkout is never cloned, patched, relabeled or cleaned by this continuation.
Normal bootstrap/Cargo invalidation remains active; no keep-stage, timestamp
repair, dependency omission or compiler-option override is introduced.

The separate continuation admission is24GiB once for the complete sequence,
under the exact campaign lock with600-second bounded admission. Every child
requires8GiB free; the existing owned supervisor polls every5seconds and stops
only its revalidated owned process group below9GiB. Between children the driver
requires9GiB. Capacity stops preserve the destination, raw commands and failure
receipt. There is no automatic retry or retirement. A new continuation attempt
requires a freshly reviewed plan and matching prerequisites.

The historical Cmono host free-space reduction from stage2 through completion
was8.925838GiB. It is neither a process allocation nor a measured peak/cap; other
host activity and between-stage changes affect it. Starting at24GiB gives
7.074162GiB nominal margin above the8GiB floor after that historical reduction
(6.074162GiB above the9GiB stop). The added stage2 all26-unit run and HIR native
history have not been measured. This budget is an explicitly bounded trial,
not a promise that the build will fit. Previously inspected Cmono intermediate
retirement receives zero credit here.

## Required sequence

1. Actual successful stage1 native history, matching compiler/source/recipe and
   exact final runtime inventory, plus its verified archive. It must include the
   successful build, three compiler identity probes, option test and run-make
   output with real verified cache-hit lines. The prior ReadyHit26 controls and
   complete324/314/318 archive chain are independently verified by reference.
2. `./x build --stage 2 compiler/rustc library --jobs 2 -vv`, then actual stage2
   `-vV`, `--print sysroot`, `-Zhelp`, binding both HIR and both partition flags.
3. `./x test --stage 2 compiler/rustc_ast_lowering --jobs 2 -vv`: all26 named
   ReadyHit units, zero ignored or filtered controls.
4. `./x test --stage 2 compiler/rustc_interface --test-args test_unstable_options_tracking_hash --jobs 2 -vv`:
   the actual named tracked-option test.
5. `./x test --stage 2 tests/codegen-units/partitioning tests/run-make/stable-cgu-partitioning tests/run-make/stable-mono-cgu-partitioning --jobs 2 -vv`:
   all15 partitioning tests and both run-makes (17total, as in the saved Cmono
   stage2 evidence; the per-MonoItem fixture is the fifteenth partition test).
6. `./x test --stage 2 tests/run-make/hir-body-cache-capture --jobs 2 -vv --no-capture`:
   actual successful run-make and visible verified tree/journal/poststate hits.
7. `./x dist --stage 2 rustc-dev rust-std --jobs 2 -vv` with full component maps.
8. Unchanged `package-owned.py --first-production`: complete runtime/std/dev,
   exact pinned public rust-src and source comparison, configured CI objcopy,
   loader probes and raw source presentation probe. The provenance identifies
   the actual stage2 source, with the complete public-base-to-source Git patch.
9. Actual packaged identity/four-capability probes, unchanged native15 and
   strip6 controls, full final package hash equality and terminal receipt.

All bootstrap commands preserve the original frozen71b495… TOML, environment,
Cargo configuration discovery absences, exact stage0/CI LLVM seeds, source and
backtrace inventory. Additional stage1 metadata produced by ordinary stage2
bootstrap is allowed after admission: the old stage1 inventory is historical
qualification, not an immutable installed toolchain. The stage2 runtime must
match its original build through packaging (the existing packager permits only
an added rustdoc executable).

`package.py` adapts HIRC's typed source inventory to the unchanged first-production
package interface. It does not call the old driver with reassigned globals. It
preserves distribution-only vendor/checksum/lock and known omission checks.
Native15 and strip6 qualify packaged partitioning and stripping with HIR flags
default-off. They do not substitute for the separate stage2 HIR actual-hit test.
The old package help check covers partitioning flags; the continuation separately
checks both HIR capabilities against the actual stage2 and packaged binaries.

Installation, interpreter tools, prepared std-MIR, strict36/source61, performance
screens and holdouts remain separate, later admissions. A complete package is
not a claim of final interpreter qualification or a0.5-second improvement.

## Review and invocation contract

First run the focused Python controls canonically after source review (unrun):
`python3 -m unittest discover -s tests -p test_hir_stage2_package.py`.
There is intentionally no published executable plan for today's failed history.
After a reviewed successful native continuation is available, the owned external
supervisor invokes this fixed shape with its actual retained paths/hashes:

```text
python3 scripts/supervise_experiment.py --run-id hir-stage2-package-plan-supervisor-01 -- \
  python3 experiments/hir-stage2-package/check.py plan --attempt plan-01 \
  --run-attempt run-01 --write-plan <THIS_WORKTREE>/experiments/hir-stage2-package/planned-stage2-01.json \
  --native-plan <REVIEWED_NATIVE_PLAN> --native-plan-sha256 <ACTUAL_SHA256> \
  --terminal <PASSED_NATIVE_TERMINAL> --native-supervisor <PASSED_NATIVE_SUPERVISOR_DIRECTORY> \
  --archive <VERIFIED_NATIVE_ARCHIVE> --manifest <ITS_MANIFEST> --summary <ITS_SUMMARY>
```

Root then reviews the emitted exact plan SHA, source, commands, capacities and
all frozen inputs before the sole run admission:

```text
python3 scripts/supervise_experiment.py --run-id hir-stage2-package-run-supervisor-01 -- \
  python3 experiments/hir-stage2-package/check.py run --attempt run-01 \
  --plan <THIS_WORKTREE>/experiments/hir-stage2-package/planned-stage2-01.json \
  --plan-sha256 <REVIEWED_SHA256>
```

The physical package belongs to the fresh run attempt under
`.work/hir-stage2-package-01/stages/run-01/packaged-stage2-01`. The parent supervisor
owns the canonical lock across every bootstrap/package/control child; nested
helpers inherit that exact file descriptor rather than reacquiring a new lock.
