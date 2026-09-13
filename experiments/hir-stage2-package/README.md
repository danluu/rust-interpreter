# In-place HIR stage2 package continuation — unexecuted

This source-only successor binds compiler `7efc0d9484da82cd327deb3b48616f8ec81eaf8d`
and checkpoint `8416694357ee7ac8ff8b1d3c262b61e7e1f52ca8`. All 27 selected
units passed. The complete native recipe then passed in a separate direct replay,
with 335 verified hits and all original output, diagnostic, edit/restoration and
version-override assertions. The original native outer attempt remains failed:
its build, option test and complete recipe succeeded, but compiletest truncated
the later hit evidence. The fixed 1,012-member archive (SHA `373719cd…`) retains
both histories, full source/runtime proof and seven verified archive references.

The new prerequisite reader verifies and reads those archived bytes. It never
falls back to historical live files, so a future PRIMARY engine merge or ordinary
stage2 replacement of rmake/support outputs cannot silently change the old proof.
The actual stage1 runtime must still match the qualified inventory at admission.
This does not relax the independent source/bootstrap/seed guards for new commands.
No new plan, Python control, compiler build or native execution has run here.

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
(6.074162GiB above the9GiB stop). The added stage2 all27-unit run and second direct-recipe execution and HIR native
history have not been measured. This budget is an explicitly bounded trial,
not a promise that the build will fit. Previously inspected Cmono intermediate
retirement receives zero credit here.

## Required sequence

1. Actual completed native replay, original successful build/option receipts,
   all 27 units and current source/runtime postguard from the fixed archive.
   Original failed status and the separate direct-recipe success remain distinct.
   All seven earlier archives are fully verified by reference.
2. `./x build --stage 2 compiler/rustc library --jobs 2 -vv`, then actual stage2
   `-vV`, `--print sysroot`, `-Zhelp`, binding both HIR and both partition flags.
3. `./x test --stage 2 compiler/rustc_ast_lowering --jobs 2 -vv`: all27 named
   ReadyHit units, zero ignored or filtered controls.
4. `./x test --stage 2 compiler/rustc_interface --test-args test_unstable_options_tracking_hash --jobs 2 -vv`:
   the actual named tracked-option test.
5. `./x test --stage 2 tests/codegen-units/partitioning tests/run-make/stable-cgu-partitioning tests/run-make/stable-mono-cgu-partitioning --jobs 2 -vv`:
   all15 partitioning tests and both run-makes (17total, as in the saved Cmono
   stage2 evidence; the per-MonoItem fixture is the fifteenth partition test).
6. `./x test --stage 2 tests/run-make/hir-body-cache-capture --jobs 2 -vv --no-capture`:
   the original successful run-make remains required. Then execute its newly built
   exact rmake binary in one fresh owned directory using the actual stage2
   compiletest environment, with full file-backed output and unchanged strict
   tree/journal/poststate hit checks. The source fixture and assertions do not
   change. Stage2 still uses the bootstrap-built `stage1-tools-bin/compiletest`
   and stage0 run-make support; only the tested compiler/std route is stage2.
   The original bootstrap receipt and direct-recipe receipt are separately bound
   in the stage2-hir record before packaging.
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

Eight focused Python controls are prepared and unrun; execute canonically only after source review:
`python3 -m unittest discover -s tests -p test_hir_stage2_package.py`.
There is no stage2 plan yet. After source review and control admission, the owned
external supervisor invokes this fixed shape with the completed replay paths/hashes:

```text
python3 scripts/supervise_experiment.py --run-id hir-stage2-package-plan-supervisor-01 -- \
  python3 experiments/hir-stage2-package/check.py plan --attempt plan-01 \
  --run-attempt run-01 --write-plan <THIS_WORKTREE>/experiments/hir-stage2-package/planned-stage2-01.json \
  --native-plan <NATIVE_EVID>/experiments/hir-arena-native-replay/planned-replay-01.json --native-plan-sha256 8cf8da2a8ece01297b14d11a8d12f1838af8df845d5f24ba902bbb072d312609 \
  --terminal <NATIVE_EVID>/.work/hir-arena-native-replay-01/stages/run-01/receipt.json --native-supervisor <NATIVE_EVID>/.work/experiments/hir-arena-native-replay-run-supervisor-01 \
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
