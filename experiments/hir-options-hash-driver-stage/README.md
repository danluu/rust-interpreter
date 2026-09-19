# Options-hash execution core

This source-only core connects the unchanged driver and fixture to the existing
finite driver supervisor and strict stdout/loader readback. No concrete plan,
freeze, standalone launcher, or actual execution exists yet. It is not a
qualification receipt.

The future enclosing stage must first validate the actual completed compiler
continuation, B3 composition and strip tests, native compiler-role controls, and
the separate run-make recipe. `check_inputs` must revalidate that complete frozen
closure. `inspect_closure` must be a frozen pure Mach-O inspector whose provider
records come from the actual qualified E2 runtime. The exact schemas for those
successful prerequisite artifacts remain to be integrated after they exist.

`controls.py` derives exactly three workload commands: one D2/B3 driver compile,
one serial driver process, and one parallel driver process. Both use E2 as their
application sysroot and runtime library provider. The ordered B3 dylib/rmeta pair
is preserved. The complete printed linker command is retained and its compiler
role arguments checked. This is an observation of rustc's printed command, not
a separate observation of a linker process.

Each real driver process uses the 120-second owned-process adapter. Its actual
PID loader trace and nine stdout records must pass the independent parsers.
Every failure stops the sequence; the parallel process never follows a failed
serial run. The two process hashes are not compared across modes.

Artifacts are confined to the new `N/native-controls/hash-driver-01` directory.
The caller supplies a fresh `hir-options-hash-driver-*` evidence directory and
the already-held canonical descriptor. The shared monitor must account for the
whole candidate namespace and every prior/current stage evidence directory.
The original 24/9/8 GiB admission/stop/floor, 14 GiB namespace, and 256 MiB
aggregate evidence constraints remain in force.

Independent source review and nine pure command/linker and mocked failure
controls passed. The failure controls confirm that a failed compile starts no
driver and a failed or unresolved serial run cannot start the parallel run.
Results and raw output are retained in `controls-01.json` and
`controls-01.stderr`. This has not compiled or executed a real driver, changed a
runtime installation, or measured an application build.
