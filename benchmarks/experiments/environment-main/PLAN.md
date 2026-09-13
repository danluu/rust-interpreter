# Publish environment support with current main

The environment/capacity tool passed 484 workspace tests per profile, 89 final
exporter tests per profile, 119 strict fixture/cache/Cargo commands, 40 existing
project history commands with byte-identical artifacts, and all 114 original
parser tests. Its saved source/component audit passed before main was merged.
Retain these proofs and their original experimental/performance scope.

Main subsequently added compiler selection and host-macro routing. Merge those
sources without replacing them. The publication worktree has the exact reviewed
20-file source/fixture delta over ca7318da; main.rs only adds the limits module.
PreparedJit's additional Rustdoc clarifies snapshot retention. A new explicitly
ignored offline emission observer exists only on the experiment branch and is
not part of production publication.

Build and run every exporter/wrapper test in debug and release from the combined
sources, with no test filter, two Cargo workers, locked/offline dependencies,
the owned shared target, 12 GiB admission and 8 GiB command floor. Both profiles
must pass the same count, at least the prior 89. Rebuild exporter and wrapper;
retain exact VM c55befb856cdb38aadb803d0d059322dbe4691b6afd6ebbc55391a28f8545306
only after bytecode source identity checks with precisely the documented
Rustdoc/ignored-test exceptions. Install a new immutable composition, never
overwrite existing tool builds.

Then qualify the combined tool on strict environment/dynamic/cache/Cargo
controls and original public/private project histories. Native assertion
outcomes, wrong edits, complete strict errors and restoration remain mandatory.
These commands qualify compatibility, not performance. Main's new compiler and
macro options retain their explicit defaults and independent qualifications.
Check the complete original parser with the new tool as well. Reuse measured
VM proofs only by exact binary identity; do not transfer old complete-command
timings to the changed launcher/exporter composition.

All substantial work holds the shared benchmark lock with 45-second admission.
No goal-state changes, unrelated process control, private evidence publication,
subagents, AWS activation or new cleanup service.
