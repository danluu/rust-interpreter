# MIR encoding for host dependencies

Suggestion4.1 identifies forced MIR encoding on every library invocation as
an unmeasured large-project build cost. The Nushell native calibration is now
complete. Investigate this independently of the current capacity-credit runtime
comparison; do not run builds or tests until that controller and both guards
finish and the shared benchmark lock admits this task.

The experimental wrapper preserves original compiler flags for an unselected
host library only when the launcher provides a nonempty std-MIR sysroot and
guest target, and the actual rustc invocation has no --target flag. Keep the
old forced-MIR policy for target libraries, selected exports, standalone use,
and incomplete/ambiguous context. Do not remove an explicit user MIR flag.
Selection, ordinary host compilation, strict frontend checks and guest MIR
requirements are unchanged. The candidate is selected by its immutable tool
key, leaving the installed baseline unchanged.

Cargo documents separate host build-script/proc-macro dependencies when an
explicit target is supplied. The wrapper already uses that separation for its
std-MIR sysroot. The actual command vectors and emitted files must confirm it
under the pinned nightly before any performance comparison.
[Cargo build cache](https://doc.rust-lang.org/cargo/reference/build-cache.html),
[target rustflags](https://doc.rust-lang.org/cargo/reference/config.html#buildrustflags).

First qualify the16 routing tests in debug/release and the installed wrapper's
real exec/PID/argument/cwd/jobserver behavior, including new host-library probes.
Build only this std-only wrapper and compose it with unchanged qualified VM and
exporter49746a22. Host qualification floor: 4 GiB. Use the shared root lock,
45-second admission and two Cargo workers; no unrelated process control.

Then use a small owned Cargo workspace where one library is both a normal and
build dependency and a proc macro has a host dependency. Record actual rustc
argv and verify distinct host/guest units. Exercise a real production edit,
original tests, an assertion-breaking edit, uncalled type and borrow errors,
restoration, and identical baseline/candidate guest artifacts. The recorder is
qualification-only and never wraps timed commands. Preserve user-specified
host flags and verify that no candidate guest dependency loses forced MIR.

Only after that qualification, freeze a complete Nushell type-relations edit
comparison: identical VM/exporter, independent baseline/duplicate/candidate
wrapper caches, native repository/line-tables and check controls, fifteen edit
pairs and A/A, fourteen original assertions, wrong edits and compiled restored
source. Predeclare storage, orders, controls, acceptance rule and held-outs
before taking timings. Report empty-target setup separately from warm edits;
no unchanged-build performance sample. No speedup or default adoption is
established by this plan or by reducing metadata bytes.
