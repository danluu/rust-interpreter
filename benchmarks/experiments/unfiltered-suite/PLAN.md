# Unfiltered fre-kernels command

Measure `cargo test -p fre-kernels` with no test filter, `--lib` restriction,
ignored-test override or source/test modification beyond the existing real
production edit. Retain O0/incremental, repository debuginfo, 18 jobs/default
threads and host-build-O0. Reuse the completed native calibration's repository
target; label the initial restored-source command as a warm anchor, not cold.

Run original source, the existing wrong token edit and the first real token
edit, then restore source. Require the whole native command to pass on original
and edited source and to reject the wrong edit through an original assertion.
Record every unit/doc-test summary and the complete selected/ignored/failing
name lists locally. Any original-source failure stops the experiment with its
logs preserved; do not filter it away. The changed-source full command is the
performance observation. This short first measurement is not a retention gate.

Compare the original native unit-test inventory with the existing retained
custom body replay's exact 389-name inventory and outcomes. Clearly label that
custom evidence as historical, with its compiler/runtime/options and limitations.
It cannot supply a new edit-to-suite custom time. The next custom implementation
must preserve per-test guest state, TLS, ignore and failure semantics and report
any unsupported harness features; direct body batches are not full libtest.

No new dependency target is created. Admit the reused native target with a
256MiB growth margin above the existing 8GiB floor, then check the floor before
each child. Keep process ownership and source restoration under the shared lock.
