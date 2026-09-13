# Native development HIR input-gate coverage

The exact qualified diagnostic driver completed ordinary pinned Cargo `check
--locked --offline --jobs 2 --package nu-protocol --lib --tests` on an isolated
clone of Nushell 9d315796, retaining its default features, profile and Cargo config.
This was a development coverage diagnostic, not the strict 14-test workflow,
a performance measurement, a holdout, or a HIR cache-hit test.

Only one function passed the exact candidate input gate in each `nu-protocol`
configuration: 1/155 free functions and 1/12,488 all resolved owners in each of
two ordinary builds; 1/1,015 free functions and 1/17,877 owners in the test build.
The same source function accounts for all three accepted records (369 source
bytes each). Output capture remains unmeasured. This narrow subset does not
justify a full compiler cache build for Nushell performance.

All 742 raw reports are retained: 726 complete normal compiler invocations and
16 probes. There were no unexplained owner gaps or exact-gate/instrumentation
mismatches. Totals are invocation-weighted, not deduplicated. Of the 726 compiler
invocations, 689 had incremental disabled and were ineligible by construction.
The 37 incremental invocations contained 70,997 resolved owners and 3,941 free
functions, with three accepted records. Summary JSON separates those denominators.

The complete Cargo command succeeded. Its original supervisor result remains
failed because the initial report classifier expected `--test`; this project's
`harness=false` lib instead receives `--cfg test`. The corrected saved-only
assessment recognizes exact argv forms, validates every retained row/count,
and requires both selected normal and test configurations. No compilation was
repeated, result removed, or diagnostic substituted. Two earlier source-only
setup failures preserved ordinary Git symlink fixtures; the same clean clone
was reused and all 2,473 tracked source entries remained unchanged.

The archive contains complete raw outputs/reports and process receipts, both
failed setups, the successful source freeze, original and corrected assessment
source, native/compiler identity guards, frozen gate/helper inputs, source
inventory and all tracked Nushell source bytes. Symlinks are stored as inert Git
link-text files, with their real target/membership proof in source-inventory JSON.
No archive member creates a live symlink. Existing native qualification remains
linked by archive hash. Actual compiler/driver binaries and generated Cargo
caches remain local. No project names participate in the mechanism's gate.

First-rejection site counts show why the current gate rejects owners; they do
not predict gains from relaxing a guard or prove that later gates would pass.
