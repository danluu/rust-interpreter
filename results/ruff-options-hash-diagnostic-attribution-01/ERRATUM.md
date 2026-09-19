# Corrected diagnostic attribution

The strict run's **13,491 capture messages are not 13,491 newly executed captures**. The original eligibility report is retained unchanged as `original-eligibility-065d.json`; its count is a literal stderr-message total.

| Scope | Executed cold captures | Replayed capture messages | Current Ruff verified hits |
| --- | ---: | ---: | ---: |
| Initial cold candidate build | 2,921 (1,510 dependencies + 1,411 Ruff) | 0 | 0 |
| Each of seven warm candidate commands | 0 | 1,510 | 1,411 |
| All eight candidate commands | 2,921 | 10,570 | 9,877 |

In every warm history, the 1,510 capture messages follow Cargo `Fresh` dependency records and precede the sole `Running` record for Ruff. Their complete ordered stream matches the initial dependency capture stream byte for byte. All six wrapper records in each warm history are accounted for: one exported Ruff compilation and five native identity/file-name probes. The fresh Ruff invocation then reports 1,411 verified hits and no cold captures. The wrong-edit command retains its original expected exit code 1.

The independent review checks 383 saved files (21,313,326 bytes), including 379 exact members of the existing 840-member strict capsule and all 355 candidate wrapper argv records. It also checks eight off-arm stderr streams contain no HIR cache events. Full raw logs stay in `../ruff-options-hash-strict-01/evidence.tar.gz`; `evidence-references.json` names every required member and exact hash. The review includes selected line-numbered context without replacing the full raw evidence.

The source review confirms that a successful hit performs current input/key preparation and checked HIR reconstruction, then returns before cold lowering/capture. Event counts are not counts of distinct functions, and a hit does not mean zero work.

This is a corrective attribution of existing diagnostic evidence. No compiler or benchmark was rerun, no original source or proof was changed, and no timing or speedup is qualified. The older profile discussion and unmeasured optimization hypothesis retained in A's original attribution report are outside this capsule's independent attribution review.
