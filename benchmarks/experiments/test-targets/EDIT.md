# Production edit through a real integration target

Use fre's original three end-greedy integration tests. Change only the production
`end_greedy_class_literal_prospective` function in `fixed_absolute_domain.rs`.
The five cumulative edits reorder pure checks, commute checked additions and
use inferred checked conversion. A separate deliberately wrong nonempty-suffix
guard must fail the original assertions natively and in the custom VM while
remaining well typed for the independent Cargo-check control. Test source stays
byte-identical, and production source is restored after the run.

Reuse completed native, custom and separate check caches. Run an original-source
anchor to prime this target, then the wrong edit and five real edits. Rotate the
three modes using the existing workflow schedule. Only the five changed-source
native/custom pairs enter the comparison; no unchanged command or cold result
is claimed. All modes use 18 jobs. Native/check preserve O0/incremental and the
repository's full/unpacked debuginfo; native uses default test threads. Custom
uses the already qualified retained MIR/inlining/resumable/persistent settings.

Require all assertions, strict checking, actual rebuilds, artifact snapshots and
source restoration. Record CPU, complete Cargo/launcher time and the independent
check floor. A median paired custom/native wall ratio at most 0.90 is the pilot
target; CPU is reported. This one-cycle result cannot retain a new engine or
establish a universal speedup. A successful pilot justifies other integration
targets and repeated histories; a failure guides the next implementation.

Admit 512MiB growth above the 8GiB floor before priming reused caches. Two older
completed native primary caches were retired after exact path/command, terminal,
open-file and preserved-evidence checks; their final test executables and all
logs remain. No archive was created. The current native and separate check
targets remain available.
