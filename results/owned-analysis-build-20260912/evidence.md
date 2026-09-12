The six sibling `owned-analysis-{token,pgrust}-20260912-0{1,2,3}` directories
are unchanged copies of the completed summaries and verifier results. Their
`raw` fields retain the original task-owned workspace paths. Original records,
checking controls, source transitions and finished-command receipts are copied
under `evidence/workflows/<run>/`. No confirmation timing or partial confirmation
history is part of this report.

`qualification.json` is the exact pre-screen qualification record. Its original
proof paths map to copied files in `evidence-manifest.json`; every expected hash
was checked while copying. The frozen compiler and baseline source manifests,
all fifteen common-control source files, tool build/install receipts, selected
versus built binary identities, qualification controllers, Rust test logs,
standalone oracle receipts and validation adapter are retained. Compiler source
itself is integrated byte-exactly from `04bb082`; the staged files reproduce the
recorded 137-file tool key. The original six-history controller and assessor
and the frozen future confirmation plan/controller/assessor are also included.

`evidence/interpreter-validation.json` is the candidate's preserved full summary
and exactly equals `qualification.json`'s `full_validation` object. It does not
replace the baseline `results/interpreter-validation.json`. The successful
validation's 23,727 original JSONL command receipts are retained in the lossless
fixed-timestamp gzip archive `evidence/validation/complete-commands.jsonl.gz`.
Before archiving, the JSONL records were compared with the original equivalent
`records.json`; they are equal. The manifest records compressed and uncompressed
hashes, byte counts, command count and the equivalent JSON file's original hash.
Reading or decompressing the archive executes no commands.

The manifest lists all 96 retained executed `.rbc` files with run, cycle, state,
mode, original path, size and SHA-256. The independent screen audit rehashed
these bytes and bound them to the launch receipts before this report was
assembled. Those artifact bytes, frozen binaries and source snapshots remain
at their existing original paths; this integration copies no large artifact
or target cache and performs no reclamation. Existing result files remain
unchanged.

Copied scripts retain their original path assumptions and are provenance, not
standalone entry points to rerun from the report directory. Their recorded
commands include the shared lock; they must not be wrapped in another holder
of the same lock. Live confirmation state is intentionally absent: the draft
status remains PENDING until both fixed confirmations have completed and been
independently checked.

Byte-preserved Rust/oracle logs contain their original trailing blank lines,
and the qualified source patch contains space-prefixed blank context lines.
These account for the full Git whitespace check's exceptions; compiler, test,
design, authored report and other copied evidence files pass that check.
The preserved proof bytes were not normalized.
