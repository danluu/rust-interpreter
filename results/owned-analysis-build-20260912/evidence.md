The six sibling `owned-analysis-{token,pgrust}-20260912-0{1,2,3}` directories
are unchanged copies of the completed summaries and verifier results. Their
`raw` fields retain the original task-owned workspace paths. Original records,
checking controls, source transitions and finished-command receipts are copied
under `evidence/workflows/<run>/`. The two sibling
`owned-analysis-confirm-{ruff,nushell-generic}-20260912-01` directories are also
unchanged complete results. Their full raw/control/transition receipts are
included alongside the screen histories; Nushell's original case snapshot is
retained as `case.json`.

`qualification.json` is the exact pre-screen qualification record. Its original
proof paths map to copied files in `evidence-manifest.json`; every expected hash
was checked while copying. The frozen compiler and baseline source manifests,
all fifteen common-control source files, tool build/install receipts, selected
versus built binary identities, qualification controllers, Rust test logs,
standalone oracle receipts and validation adapter are retained. Compiler source
itself is integrated byte-exactly from `04bb082`; the staged files reproduce the
recorded 137-file tool key. The original six-history controller and assessor
and the original frozen confirmation plan/controller/assessor are also included,
with the final completed confirmation controller, exact assessment, source
preparation receipts and all controller/plan proof mappings.

`evidence/interpreter-validation.json` is the candidate's preserved full summary
and exactly equals `qualification.json`'s `full_validation` object. It does not
replace the baseline `results/interpreter-validation.json`. The successful
validation's 23,727 original JSONL command receipts are retained in the lossless
fixed-timestamp gzip archive `evidence/validation/complete-commands.jsonl.gz`.
Before archiving, the JSONL records were compared with the original equivalent
`records.json`; they are equal. The manifest records compressed and uncompressed
hashes, byte counts, command count and the equivalent JSON file's original hash.
Reading or decompressing the archive executes no commands.

The manifest lists all 160 retained executed `.rbc` files with run, cycle, state,
mode, original path, size and SHA-256. The independent audits rehashed these
bytes and bound them to the launch receipts before this report was assembled:
96 from the screen and 64 from the confirmations. Those artifact bytes, frozen
selected binaries and source snapshots remain
at their existing original paths; this integration copies no large artifact
or target cache and performs no reclamation. Existing result files remain
unchanged.

Copied scripts retain their original path assumptions and are provenance, not
standalone entry points to rerun from the report directory. Their recorded
commands include the shared lock; they must not be wrapped in another holder
of the same lock. The prospective plan retains its original pre-execution
language unchanged; `confirmations.json` and
`confirmation-independent-audit.json` record the completed passing outcome.
All outliers and the difference between fifteen Ruff pairs and three Nushell
pairs are retained. Paired bytecode equality holds in every state, while both
verifiers explicitly record some cross-cycle artifact differences.

`evidence/owned-analysis-built-vm-preservation.json` and its retention
controller/log/script record the separately built, unselected VM's byte-exact
copy to a task-owned retained path before later build-target reuse. The small
receipts are copied here; the binary itself stays at that recorded path.
Its SHA-256 remains `1301b8b...`; all measured and differential-validation
launches selected the baseline VM with SHA-256 `03d401c...` instead.

Byte-preserved Rust/oracle logs contain their original trailing blank lines,
and the qualified source patch contains space-prefixed blank context lines.
These account for the full Git whitespace check's exceptions; compiler, test,
design, authored report and other copied evidence files pass that check.
The preserved proof bytes were not normalized.
