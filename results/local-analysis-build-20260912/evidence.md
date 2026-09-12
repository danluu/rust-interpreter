The six sibling `local-analysis-{token,pgrust}-20260912-0{1,2,3}` result directories
are unchanged copies of the completed summaries and verifier results. Their
`raw` paths continue to identify the original task-owned workspace.

`evidence/workflows/<run>/` contains each history's original `records.json`,
`check-records.json`, `source-transitions.json`, and final `active-command.json`.
The latter is a finished-command receipt, not an instruction to control a process.
Controller logs and verification logs are copied alongside the controller JSON
and the exact prospective/continuation/assessment script sources. Archived
scripts retain their original relative-path assumptions and are evidence, not
standalone entry points to rerun from this report directory.

`qualification.json` is the exact pre-screen qualification record. Its original
`.work` proof paths map to copied files through `evidence-manifest.json`. Rust
test logs, tool build/install records, frozen source manifests, standalone oracle
receipts and both validation adapters are included. The successful summary in
`evidence/interpreter-validation.json` comes from the preserved full-summary log
and exactly equals `qualification.json`'s `full_validation` object. It leaves
`results/interpreter-validation.json` at the report branch's baseline version.

The successful validation's 23,727 original JSONL command receipts are retained
as `evidence/validation/complete-commands.jsonl.gz`. The failed adapter run's
8,176 receipts are retained separately as
`evidence/validation/initial-adapter-failure-commands.jsonl.gz`. These are
lossless gzip archives with fixed timestamps. The manifest records archive and
uncompressed SHA-256 digests, byte counts, command counts, and the hash of each
original equivalent `records.json`. The JSONL and JSON records were independently
compared before archiving. Reading or decompressing them executes no commands.

The manifest also lists all 96 retained executed `.rbc` files, with run, cycle,
state, mode, path, size and SHA-256. Their bytes remain in the original raw
workspace; tools and compiler source snapshots remain in their existing frozen
locations. The independent audit rehashed all artifacts and bound them to the
launch receipts. This report copies evidence and does not reclaim or alter any
cache, executable, artifact or source snapshot.
