# Six completed workflows; final workflow interrupted by ENOSPC

The seven-workflow corpus `resumable-bulk-heldout-01` is incomplete. Its last
case, Nushell type relations, failed to write an active-command receipt, then
failed to restore the source. Corpus and supervisor status publication also
failed, leaving stale `running` receipts. Those original receipts and logs are
preserved here, with hashes in [summary.json](summary.json).

Recovery found no matching live run processes, no open source file or process
working in the source root, and an available benchmark lock. The source matched
the exact recorded cycle-zero state-two mutation. The owned snapshot and Git
pin were verified, and the original source was restored by an atomic rename.
No process was signaled, cache removed, or other work controlled. About 90.8 GiB
was available at recovery; the underlying disk-capacity fluctuation is unexplained.

All six completed case receipts were independently reproduced without changing
them: 378 primary commands, 126 checking controls, 90 edited pairs, 252 paired
artifacts. Median within-edit candidate/baseline wall changes were pgrust −1.88%,
Nushell +0.60%, private rg-aot −0.03%, fre TLS −1.58%, pgrust SHA-1 −4.38%,
Ruff −0.56%. None exceeds the 5% regression threshold. These small deltas are
not significance claims, and six cases do not establish a seven-case pass.

The incomplete case preserves 12 primary records and three completed checks.
Its fourth check was launched but has no completed receipt; its outcome is
unknown. Do not combine these partial timings into the completed-workflow totals
or silently discard them when retrying. A retry must use a fresh run and cache
namespace, the same runtime/control settings, and all three cycles and five edits.
The original token performance gates remain failed and the runtime stays experimental.

The Nu-protocol test dependency graph also includes host rebuilding:
`nu-test-support` depends on `nu-cmd-extra`, whose build script depends on
`nu-protocol`. The actual builds included regular host and guest library units.
The theme-generating build script is real workload cost and must remain enabled.
The pinned Cargo check fingerprint confirms that `check --lib --profile test`
selects `test-lib-nu_protocol`; that command does not need a target-selection fix.

The harness now stages original bytes before mutation, publishes source/JSON
updates atomically, drains and waits for children on receipt-publication failure,
and checks for at least 8 GiB free before each command. This is a preflight check,
not a disk reservation. Same-directory restoration can still fail on filesystem
metadata errors; the staged original is retained with a recovery path. Host or
process termination still requires recovery inspection.

[Fault-injection checks](../workflow-io-faults-01/summary.json) cover partial writes,
source restoration without allocating new payload, external edits, altered backups,
and three real child lifetimes, including full stdout/stderr pipes. All ten pass.
These are harness checks; the retry will exercise the integrated Rust workflow.
