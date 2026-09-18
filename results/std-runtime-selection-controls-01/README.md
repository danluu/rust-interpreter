# Runtime compiler selection for standard-library preparation

`scripts/std_mir_source_paths.py` now accepts an explicit
`--runtime-compiler-key` as an alternative to `--compiler-key`. The former uses
the separately installed runtime namespace; the latter retains its complete
stage2 loader. Both use the same preparation function, source capability checks,
canonical workload lock and final compiler revalidation. A failed lookup or
preparation never falls back to another compiler.

All 23 focused controls passed: five new CLI selection controls and the eighteen
existing source-path preparation controls. The existing controls include runtime
policy revalidation, missing source-capability rejection, changed installation
rejection, exact source snippets and retained failures without readiness.
Supervisor process 18902 ran test process 22809. No native compiler or Cargo
process was executed; these are synthetic controls, not application qualification
or build-time measurements.

`evidence.tar.gz` retains all 183 evidence members, including raw test output,
the child receipt, the test runner and all local Python module snapshots.
Every archived member was read back and checked against `manifest.json`; the
gzip stream was checked through EOF. `summary.json` records the actual test
names, invocation, environment and timestamps.

The selected installation must belong to the CLI's checkout. Keys do not select
installations in another worktree. This change does not publish an exporter or
add runtime compiler selection to the application launcher.
