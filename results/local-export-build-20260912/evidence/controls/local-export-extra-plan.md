# Candidate 5 audit and inlining qualification

This is unexecuted source preparation for candidate key
`14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75`,
compared with the published `eb91912d` baseline. Candidate 4 controls, artifacts
and results stay unchanged. No diagnostic capacity/preparation results are
substituted for candidate 5 correctness evidence.

After actual core qualification passes 408 Rust tests with zero failures and one
ignored test per profile, plus all 23,727 differential commands, run
`validate_local_export_extra.py freeze`. It imports no validator and exclusively
writes `local-export-extra-controls.json`, binding core proofs, both installed
bundles, the reviewed static inputs, exact commands, and the optional historical
exporter-capability rejection branch of the original inlining test. The candidate
VM and wrapper must equal the baseline bytes.

The existing `scripts/validate_audit_artifacts.py` and
`scripts/validate_leaf_inlining.py` stay byte-identical. Their adapter changes
only `checked_tools` to the frozen candidate bundle. Preserve all native and
interpreter/JIT comparisons, copied-source edits, feature/selection changes,
strict rejections, cold panic diagnostics, audit metadata and retained-program
provenance, corruption/missing-body controls and original recovery assertions.
The audit validator performs 79 commands. Inlining performs 23 commands, plus
its existing optional old-exporter rejection if the corresponding owned bundle
is present at freeze. Freeze records that branch; later changes reject launch.

The copied eight-export audit parity check retains the original Result fixture,
six requested entries, four lowered and two blocked outcomes, inlining off/on,
retention off/on, optional false flags expressed by absence, source crate name,
compiler arguments, alternating baseline/candidate order and report comparisons.
Only existing timing fields and generated pack directory names are normalized.
It requires eight corresponding artifact pairs (16 separately verified files).
It does not execute audit bodies; independent execution comes from the full
audit and leaf-inline validators.

Run these three jobs through the established `run_locked.py`, sequentially:

- Label `local-export-audit-tests`, command from controls: Python plus
  `validate_local_export_extra.py audit`.
- Label `local-export-inline-tests`, command from controls: Python plus
  `validate_local_export_extra.py inline`.
- Label `local-export-audit-parity-tests`, command from controls: Python plus
  `validate_local_export_audit_parity.py`.

These validators do **not** self-lock; they require that outer shared lock.
This differs from the separate self-locking reuse/cache and panic protocols,
which must never be nested under `run_locked.py`. Any lock timeout leaves the
job unstarted; retain its controller evidence before retrying the same command.
A started failure remains evidence and is not silently rerun or overwritten.

Fresh `local-export-*` adapter/validation receipts and timestamped validator
workspaces retain every command. The paired-export directory is exactly
`B/local-export-audit-parity`. Preserve any prior top-level audit summary as
`local-export-audit-prior-top-level.json`, retain the new summary separately as
`local-export-audit-top-level-validation.json`, and restore the prior bytes even
when the validator fails. No prior candidate output is replaced.

Finally run `qualify_local_export_extra.py`. It verifies exact wrapper argv,
owner/cwd, child identity and terminal times after the control freeze; original
counts, restored source, paired reports and artifact hashes; and all frozen
proofs. It writes `local-export-audit-inline-passed.json` exclusively, containing
`status: passed`, both full keys, checks/counts, and a ROOT-relative SHA256 proof
map. The total is 110 commands, or 111 with the frozen optional old-tool check.

This receipt covers only audit artifacts, inlining and audit parity. Adoption
must separately require actual reuse/dependency/cache passes and
`local-export-panic-passed.json`; a panic execution receipt still awaiting manual
structural inspection is insufficient. No performance or holdout claim follows
from these correctness checks.
