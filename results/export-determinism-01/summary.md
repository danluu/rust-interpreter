# Deterministic scheduling of function-pointer bodies

The exporter used a randomly seeded HashMap to schedule address-taken functions when an indirect-call signature became needed. Lowering those bodies can discover further functions and constant allocations. Different map iteration orders therefore changed later function IDs and data offsets even when the Rust source was unchanged. The map now uses BTreeMap with assigned function IDs as keys. Type checking, borrow checking, function selection and guest runtime behavior remain the same.

The defect surfaced when the Ruff native-fill comparison required byte-identical exported artifacts. Its first cold pair produced two different 4,465,356-byte artifacts; 71 functions moved within the 1,605-function table, and constant data also differed. Both selected-test commands passed, but the benchmark stopped before any production edits. Its three cold commands and artifacts remain in `.work/runs/e2e-paired-ruff-jit-local-fill-broad-01/`. They are not included in a performance result.

A focused fixture takes eight callback addresses before its first indirect call; each callback discovers a distinct helper. Twelve fresh exports with the old build produced twelve different artifact hashes. After the fix, each configuration below produced one hash across eight fresh compiler processes. All emitted variants were also executed against native outputs for ten boundary inputs in both custom engines.

| Configuration | Old distinct hashes / exports | Fixed distinct hashes / exports |
|---|---:|---:|
| mir0-inline0 | 3 / 3 | 1 / 8 |
| mir0-inline1 | 3 / 3 | 1 / 8 |
| mir3-inline0 | 3 / 3 | 1 / 8 |
| mir3-inline1 | 3 / 3 | 1 / 8 |

The focused comparison passed 926 commands. A separately built comparison baseline with the old JIT and the same deterministic exporter passed another 674 commands and emitted byte-identical fixture artifacts. Its VM hash equals retained build 4227fc; the candidate VM hash equals native-fill build 2df145. The source and mutable release build were restored to the candidate before further validation.

This change is a reproducibility fix, with no performance claim. The complete production-edit corpus must be restarted using the deterministic exporter in both builds. The artifact-equality check remains enabled; diagnostic function-order normalization is not used to bypass it. The focused test is `scripts/validate_export_determinism.py`, with source in `tests/function_order_fixture.rs`. All five production source pins are restored.

[Earlier native-fill compute comparison](../paired-jit-local-fill-e2e-01/summary.md), [same-artifact runtime screen](../jit-local-fill-runtime-01/summary.md).
