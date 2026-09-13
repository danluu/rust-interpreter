The six sibling `local-export-adoption-{token,pgrust}-20260912-0{1,2,3}`
directories are unchanged copies of the completed summaries and verifier
results. `evidence/workflows/<run>/` contains their exact raw primary/check
records, source transitions and final finished-command receipt.

`measurement.json`, `qualification.json`, `prospective-plan.md` and both
independent-audit files are unchanged copies. `evidence/controls/` preserves
the original fixed controls, host-test/build/install receipts, qualification
summaries, source/tool manifests, unstarted lock-timeout attempts, earlier
panic-coverage failure and later successful structural inspection.
`evidence/recovery/` preserves the separate recovery plan, manifest, scripts,
controller, logs and original byte-exact protocol copies. Archived scripts are
evidence with their original path assumptions, not entry points to execute here.

`evidence/validation/complete-commands.jsonl.gz` losslessly preserves the full
23,727-command JSONL. Each parsed record was compared with the original
`records.json` before compression, and decompression was checked byte-for-byte.
The manifest includes both original hashes/sizes and the archive hash/count.
The preserved top-level validation summary stays inside this report; the
repository's existing `results/interpreter-validation.json` is unchanged.

`evidence/qualification-text.tar.gz` contains every remaining named textual
qualification proof, including original command records, raw stdout/stderr,
actual MIR dumps, audit/census reports, checker inputs and pinned-toolchain
inspection excerpts. Its 2,362 members have fixed archive timestamps and a
per-member original-path, SHA-256 and byte-count mapping. Every member was
decompressed and checked against that mapping. Reading these archives executes
no experiment command.

`evidence/candidate-source.patch` is the exact full-index binary-capable Git diff
from published baseline `b0a3f17…` to failed candidate `2c61f295…` across 34
source/design/fixture paths. It was not applied. Compiler sources, tests, common
scripts and existing results in this report branch remain at its main parent.

`evidence-manifest.json` joins direct copies, archived members, the complete
validation archive and all 3,398 independently checked experiment proof paths.
Its 886 external-only bindings retain compiler/public-source snapshots,
executables, bytecode/cache artifacts and std-MIR metadata in their original
locations. It separately preserves all 96 screen artifact receipt tuples.
No executable, `.rbc`, cache binary or `.rmeta` was copied or reclaimed.

The post-screen integration receipt records the audit's completion before root
prepared a distinct compiler candidate. If a live compiler/fixture path later
changes, its historical binding resolves to the retained 14af snapshot or exact
`2c61f295…` Git blob, as recorded in the manifest. This does not describe an
in-run source change or extend the failed candidate's qualification to later
source.
