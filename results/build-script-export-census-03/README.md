# Build-script export census after getcwd support

The qualified exporter at source `c176cc5cd8228bdb2911a3438b51455b9acd5695`
gets past the previous `getcwd` blocker in the unchanged build-script fixture.
The next first lowering blocker is `libc::unix::fstat` in the default and
shared-helper configurations, and `libc::unix::_exit` in the configuration
that requests a subprocess. Later unsupported operations remain unknown.

The metadata plan admitted zero compiler children and retained 231 logical
source/proof snapshots. Its execution admitted four compiler commands: genuine
helper metadata generation and three strict, nonexecuting `main` lowering
audits. All four commands succeeded and all three audits correctly reported
their lowering blocker. This did not run a guest or native build script, Cargo,
or the VM, and supplies no build-time result.

The exporter and VM identities are bound to the preceding getcwd qualification
(540 Rust tests and 33 native comparison children). All 207 built-source
snapshots come from that verified archive. Current executable Python helpers,
compiler/standard-library/loader inputs, dependency sources and the unchanged
14-file fixture remain guarded. No live Rust source from an advancing worktree
is substituted for the source of the qualified binaries.

The archive retains the exact plan, four raw compiler receipts and their
stdout/stderr, three reports and matching sidecars, actual helper metadata,
both supervisors, source snapshots and launcher records. It references the
immutable getcwd qualification, native fixture baseline and preceding census
archives. The preceding archive preserves the unexecuted first draft and the
completed original getcwd-blocked census. Compiler and VM binaries are recorded
by identity rather than copied into this archive. Every member is read back
and checked against `manifest.json`.

Bindings:

- Plan: `b1041da1913f0179cd8ad550264ed1cd50d989718da837b0466c4427094bf9d5`.
- Plan receipt: `557371ffa3bd37aa40e5368c84610e60b3607d059db4584c6c994dcfb3207708`.
- Run receipt: `5f1dda60b0955ce8f7a017de228d5e46c229ee197c08611bcc0faa67ee3fbf68`.
- Observations: `491e3b71263cd2e8e494940cc33a5d3671ae0b3d85272291d3ba9cfec894de4e`.
