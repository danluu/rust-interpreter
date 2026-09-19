# Hash-stage preparer handoff

`prepare.py` is source only and has not been executed or imported. It requires
four supplied audit paths and exact SHA-256 values, each with `status=verified`
and a digest binding its actual passed compiler/B3/native/run-make receipt.
Missing future outputs fail before provider discovery. No artifact hash is
invented and no compiler, provider probe, recipe or driver runs here.

Discovery uses the canonical 600-second lock, 16 GiB entry and 9 GiB live floor.
The eventual three-child launch retains 24/9/8 GiB and the shared 14 GiB namespace
and 256 MiB aggregate evidence caps. Source/input discovery is bounded to
180,000 ordinary files, 8 GiB total input bytes, 1 GiB per ordinary payload and
256 MiB per JSON. These are read/hash bounds, not promised free-space reserves.

The preparer adopts complete transitive input catalogs with original hashes and
identities, metadata SDK/source/routes, all three compiler/provider trees,
actual native/private-pair evidence, retained recipe outputs, explicit imported
Python files and every existing candidate-stage evidence root. It runs the
controller's read-only guards and prerequisite parsers on the concrete frozen
proposal before publishing `launch.json`. It never calls `Stage.__init__`,
`execute`, or the workload core and never creates the driver evidence/artifacts.

The O run-make adapter is being migrated to the final compiler continuation03;
completed executable wiring still requires separate review. The preparer refuses
an adapter pointing to02. Native and run-make audit paths are intentionally
required arguments because no actual successful receipts/audits exist yet.
The native plan is expected to expose the `environment`, `clang`,
`runtime_closure.libraries` and relative `ordered_driver_destinations` consumed
by its reviewed recipe/controller. The discovery preflight checks those actual
schemas rather than converting guessed future values.

After the initial handoff, the parent added bounded source/proof selection and
retention to the preparer and enclosing controller. It also derives the direct
rustc environment explicitly from the actual native predecessor and records
every omitted bootstrap-only key. `prerequisites.py` and the three-command core
remain unchanged. Actual preparation and workload execution remain unrun.
