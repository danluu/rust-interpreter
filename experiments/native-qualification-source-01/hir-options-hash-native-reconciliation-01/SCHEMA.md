# Read-only native evidence reconciliation

This is a source proposal. No reconciliation has run and no qualification is
claimed. The native03 attempt remains failed, with no result in its original
namespace. Its twenty actual commands will not be repeated.

Source: `A/experiments/hir-options-hash-native-reconciliation-01`.
Evidence: `A/.work/hir-options-hash-native-controls-reconciliation-01`, which is
inside the unchanged monitor's native evidence prefix.
Fresh outputs: `receipt.json` and `native-controls.json`.

The original command owner is
`A/.work/hir-options-hash-native-controls-03`, with its original frozen source at
`A/experiments/hir-options-hash-native-controls-03`. Its receipt SHA is
`76fe70afd8eb6486b445e39366de2dd1ffd52ed9578e63203dc7cf74a679a272`.
It completed all twenty expected return codes and restored the fixture, then
failed at the late diagnostic parser. Its exact terminal error remains
`ValueError('wrong-B3 failure is not compiler metadata incompatibility')`.
The independent retained-failure audit is
`A/.work/native-controls-failure-verification-03.json`, SHA
`1058d64e64d75748a3da12115a8400a01daa5cd499b39b09c8d29520eaab4f24`.

The compact new `inputs.json` has the ordinary `files`, `links`, `absent_paths`,
and `plan_sha256` fields for its delta, plus `base_inputs: {path, sha256}` pointing
to the original03 inputs SHA
`8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d`.
All 106432 base file records and their routes/absences remain subject to full
current-byte validation. A compact reference does not omit that validation.
The delta includes the original failed audit attempt and the PID-aware successful
failure-audit execution, their source and raw records, the new parser, and its
complete source/control qualification. The new plan is in the delta and bound by
the ordinary `plan_sha256` field.

The new plan preserves every original03 plan value, including its twenty
historical `children` expectations, then adds `read_only_reconciliation: true`,
`actual_workload_children: 0`, `base_inputs`, `command_evidence`, and
`reconciliation`, plus `wrong_beta_providers`, `wrong_beta_lib`, and
`reconciliation_evidence_roots`. These are exactly eight additional keys. Those
historical expectations are never launched by the new
controller. Environment, compiler/provider roles, namespace, exact recipe,
source identity, and capacity parameters therefore retain their original values.

`wrong_beta_providers` is the complete selected list of `{path, size, sha256,
identity}` rows from the admitted B308 output inventory and original03 freeze,
for files `lib(std|std_detect|core|compiler_builtins)-<hash>.(rmeta|rlib|dylib)`
in `wrong_beta_lib`, the exact canonical beta standard-library directory. The
old `beta_std_paths` is unchanged. Parser compiler versions are the first lines
of the original `build_version` and `runtime_version`. The new monitor uses
`reconciliation_evidence_roots`, containing all original roots and the fresh
reconciliation root, with any additional existing task roots explicitly bound.
The original historical `evidence_roots` value is preserved.

The new delta's absence guards include the original03 evidence directory's
`native-controls.json`. The original failed attempt must never acquire a result.

The plan, new receipt, and new result contain the same `command_evidence` object:

```text
source: original03 source directory
evidence: original03 evidence directory
receipt_sha256: exact original failed receipt SHA
inputs_sha256: exact original03 inputs SHA
plan_sha256: exact original03 plan SHA
snapshot_plan_sha256: exact original03 snapshot projection SHA
status: failed
error: exact original late parser error
commands: exact ordered twenty original receipt references
failure_audit: {path, sha256} for independent retained-failure audit1058d64e
```

They also contain the same `reconciliation` object:

```text
source: fresh reconciliation source directory
base_inputs: {path, sha256}
original_parser: {path, sha256} for frozen03 observations.py
parser: {path, sha256} for fresh wrong_beta.py
parser_controls: {source, evidence, receipt_sha256, result_sha256, controls, audit}
failure_audit: {path, sha256} for independent retained-failure audit1058d64e
```

`parser_controls.audit` is an ordinary `{path, sha256}` reference to actual passed
control evidence, not a proposed or synthetic test result. The original parser
hash is `5aea2b1b965ee9e95a67513120ca88ab4117c0488c28b320e70c7239aeed241c`.
Future parser/control hashes are bound only after their bytes exist and review
and execution complete.

The new successful receipt will truthfully report `commands: []`,
`actual_workload_children: 0`, `saved_actual_children: 20`,
`historical_failed_children: 11`, `read_only_reconciliation: true`, the ordinary
new `inputs_sha256`, `plan_sha256` and `result_sha256`, and its own read-only
`pid`, `parent_pid`, `started_at`, `admitted_at` and `finished_at` observations.
Its `status: passed` applies only to reconciliation. It will set
`native_roles_and_behavior_qualified: true` only after full saved evidence,
source/loader/provider/artifact/restoration validation and the corrected parser
all succeed. The old failed receipt and absence of its old result remain guards.

The result retains the intended original native result fields: status
`native-roles-and-behavior-qualified`, original candidate/source/assembly/compiler
bindings, stock and source derivation, both earlier `prior_failed_attempts`, the
nine `loader_route_controls`, loader proofs, runtime closure, seven fixture
compilations represented by the original history, four native executions, four
reuse observations, E0308 parity, restored source, historical `history` of eighteen
commands, and two `wrong_B3_commands`. `wrong_B3` is the corrected saved diagnostic
proof. It adds the explicit provenance objects above. Counts are
`total_actual_native_children: 31` and `qualified_native_children: 20`; there are
eleven earlier failed children and twenty existing commands interpreted by this
reconciliation, with zero additional compiler or native invocations.

Snapshot qualification distinguishes the original payload from the new read-only
receipt. The original03 projection, manifest, gzip blobs and failed snapshot
owner remain under the original03 paths, bound by `command_evidence` and the
retained-failure audit. A downstream reusable snapshot catalog additionally
requires `qualification: {source, evidence, receipt: {path, sha256}, result:
{path, sha256}, audit: {path, sha256}}` for the completed reconciliation. No caller
may replace the original snapshot owner's failed status with a synthetic passed
native03 terminal.

The corrected parser preserves byte-for-byte wrong-role output parity and E0514
code checks, requires an original selected std/core provider, and additionally
accepts `compiler_builtins` only with exact source-defined note/help structure and
current verification of every named admitted B3 provider. Compiler identity,
foreign paths, unknown codes/crates, missing providers and unrelated diagnostics
remain rejection conditions. The generic source definitions and actual complete
018/019 streams are bound in the focused control packet.
