# Large-project native control: Nushell type relations

Compare the pinned Nushell nu-protocol fourteen original type-relation tests
under repository debuginfo, an independent identical repository A/A cache,
and line-tables-only. Both debug settings use the current unpacked split
format; preserve optimization, incremental compilation, assertions, overflow
checks, dependencies and default libtest concurrency. Match two Cargo workers.
Include cargo check as a distinct control. No custom tool or linker changes.
This measures one practical native control, not the fastest possible native
build and not a claim that the custom engine beats it.

The existing effective-profile receipt shows full debuginfo in Nushell and
line tables already in Ruff. Verify actual unit-graph profiles before timing,
including all non-debug fields. Use repository settings directly; the old O0
control happens to match Nushell's dev settings but is not silently imposed.
A changed Cargo/profile structure fails preflight rather than changing this
comparison. Compile no code during the unit-graph queries.

Run three rotated cycles of original source, one known wrong production edit,
and five cumulative real edits, followed by compiled restoration: 88 complete
commands, fifteen paired edited observations and fifteen A/A pairs. Preserve
all fourteen original assertions and the complete test module. Require a real
crate rebuild/check in every command. Check accepts the semantically wrong
edit; native tests must fail with the expected original test outcomes. Report
rounded libtest suite time and command residual separately. Do not substitute
an unchanged run or isolated executable timing for complete Cargo commands.

The control does not need an8% optimization gate. Report paired wall/CPU
ratios, per-edit variation and same-session A/A envelopes (largest absolute
per-edit median departure). Mark noise above4% wall or3% CPU explicitly and
preserve all observations. Do not select a fastest preset per edit, overwrite
an earlier result, splice incomplete pairs or repeat to cross a threshold.
Line tables preserve source locations but reduce debugger variable/type data;
repository settings remain an equally visible control.

Storage admission: four targets each conservatively estimated from the
completed type-relations native cache's5,820,945,967 unique bytes, with20%
growth,16MiB evidence and8GiB free floor: about34.04GiB. Check is deliberately
budgeted as a full native target. This is an estimate, not a reservation against
other workloads. Require8GiB before each child. No source edit or build starts
on failed admission. Shared benchmark lock admission is bounded to45seconds.
Do not interfere with other workloads or retire caches as part of this run.

Run after the call-protocol comparisons and owned counter probe have released
the shared lock. Publish this calibration independently of whether the runtime
candidate passes. A later custom/main comparison must use this stronger native
control in the same session before making a new relative-speed claim.
