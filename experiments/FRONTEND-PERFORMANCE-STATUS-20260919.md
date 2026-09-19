# Frontend optimization status, September 19

Neither compiler candidate below has a measured application speedup yet. No new
result establishes a warm edited build below 0.5 seconds. Correctness checks and
installation work are separate from application build timings.

| Candidate | Completed checks | Remaining performance evidence |
| --- | --- | --- |
| Cache the immutable incremental option hash once per compiler context | Compiler build; serial and parallel hash controls; compiler behavior controls; audited runtime installation07 and standard-library preparation07 | Prepare and qualify the exporter, then real edited Ruff builds with HIR caching off/on and independent holdouts |
| Retain the first ordinary procedural-macro arena page across reset | Corrected native and Miri checks; real macro callers against both N client libraries; default sysroot discovery; all 36 native frontend timings and restoration checks independently verified | Parked: median improvement 0.5894% did not exceed 3.4410% stock/stock variation |

The hash candidate retains the complete original hash and its wire encoding.
The arena candidate retains only an ordinary first page after clearing interned
references. Neither change selects applications, omits compiler checks, or edits
Ruff or Nushell to obtain a speedup.

The completed arena measurement has six blocks, twelve stock/candidate pairs
and six stock/stock pairs: 36 timed compiler calls. Twelve untimed warmups,
twelve restoration checks and two Cargo setups remain separate. The observed
candidate/stock median is 0.9941062; the fixed comparison rule rejects this as a
performance win. No unchanged retry is allowed. A native nonincremental frontend
screen cannot establish the full interpreter edit-to-run target.

The first two screen attempts stopped during Cargo setup. Attempt 01 rejected
Cargo's ordinary `-Z embed-metadata=no`; attempt 02 rejected a build-script
command with no `-C extra-filename`. Attempt 02 completed three compiler queries
and one dependency compilation. Neither attempt reached an edit, warmup or timed
sample. Attempt 03 completed both Cargo setups, with 325 compiler invocations
per arm, and compiled the edited source successfully in its first warmup. Its
reader then rejected a normal `unused_extern` JSON record; no timed samples ran.
Original arguments and failure records remain retained. Successor harness
changes must preserve those arguments, all diagnostic records and the fixed
comparison rule.

Attempt 04 accepts all four JSON record kinds selected by the captured Cargo
command and compares every ordered nonartifact report across the paired arms.
The parser passed checks against three unchanged captured streams, five valid
fixtures and 29 malformed-output cases before the timed screen. The screen
completed successfully; its timing outcome is reported above. Neither the parser
checks nor this screen qualify full application behavior or edit-to-run latency.

Runtime installation06 also stopped before completion. Its ten loader probes
returned successfully, but the reader concatenated three architecture sections
from four universal macOS libraries while the specification described ARM64.
The failed prefix remains intact. The correction explicitly selects the admitted
host architecture and binds that policy into a distinct runtime identity.
Eighteen focused policy, identity and recipe checks passed, followed by two
ordinary runs of 30 installation and factory checks. Integration source and both
development runs passed independent review. All 48 controlled checks and their
independent audit also passed. Production installation07 passed all 15 probes:
ten native loader checks, three compiler information checks and two expected
source-probe errors. Its independent saved-output audit12 failed because the
reader declared provider directories from file and symlink ancestors, omitting
two empty directories correctly retained by the installer. All file and symlink
paths were covered. Successor audit13 declares complete directory metadata from
the saved admission record and passed against the unchanged installation. It
verified all 944 provider directories, all 3,708 installed files and their
636,631,680 bytes, and the original 15 child results. Its nine new regressions
and 326-file source-manifest preparation also passed. The earlier 29 regressions
were not rerun; the original failure stays retained. These results establish
installation correctness, not application behavior or build speed.

Standard-library preparation07 passed its seven expected commands, including
native and prepared E0080 source-location checks. Independent readback verified
all 3,644 copied library source files and 3,670 prepared sysroot files, along with
the exact commands, environment, retained inputs and terminal receipts. The
ordinary CLI retained ownership of its workload and standard-library locks.
Exporter qualification and strict application histories remain pending.

Exporter preparation passed after restoring five exact saved VM proof files
missing from the sparse working tree. The initial failed attempt remains saved.
All 36 subsequent metadata commands completed successfully, but the result
reader rejected dyld's delayed-load transition messages. That metadata attempt
is closed and failed. The lossless parser correction passed all 24 controls,
including both complete saved streams; the corrected metadata attempt has now passed.
No exporter build or application timing ran in the failed attempt.

The successor preparation retains five exact sparse-checkout proof paths across
main merges. Metadata02 passed all 36 commands, and build02 passed its ordinary
locked/offline exporter build and six tool checks. All 34 frontend correctness controls passed, including bytecode parity and
nine diagnostic comparisons. Tool publication passed all three fresh checks; strict Ruff
application qualification remains pending. These preparation checks provide no application timing result.

Evidence entry points:

- [Option-hash change and semantics](hir-options-hash/README.md)
- [Actual serial/parallel driver controls](../results/hir-options-hash-driver-02-publication/STATUS.md)
- [Passed saved runtime preflight audit](../results/runtime10-preflight-saved-audit-01/STATUS.md)
- [Passed installation resource and admission controls](../results/runtime-installation-controls-07/STATUS.md)
- [Actual macro-client default discovery checks](../results/proc-macro-arena-n-overlay-01-publication/STATUS.md)
- [First Ruff setup failure](../results/proc-macro-arena-ruff-screen-01-publication/README.md)
- [Second Ruff setup failure](../results/proc-macro-arena-ruff-screen-02-publication/README.md)
- [Third screen's frozen source and protocol](proc-macro-arena-ruff-screen-03/README.md)
- [Third screen's closed failure evidence](../results/proc-macro-arena-ruff-screen-03-publication/README.md)
- [Corrected JSON parser development checks](../results/proc-macro-arena-ruff-screen04-parser-development-01/STATUS.md)
- [Completed native frontend screen: allocator path parked](../results/proc-macro-arena-ruff-screen-04-publication/README.md)
- [Failed runtime installation](../results/runtime-installation06-failure-01/STATUS.md)
- [Native loader correction development checks](../results/runtime-native-loader-development-01/STATUS.md)
- [Installation integration and both development runs](../results/runtime-installation07-source-development-review-01/STATUS.md)
- [Passed current integration controls and independent audit](../results/runtime-installation-controls-08/STATUS.md)
- [Installation auditor source and passed ordinary regressions](../results/runtime12-installation-audit-source-01/STATUS.md)
- [Passed installation07 and retained audit12 failure](../results/runtime-installation07-success-01/STATUS.md)
- [Corrected directory reader and nine new regressions](../results/runtime13-provider-directory-source-01/STATUS.md)
- [Passed audit13 of the unchanged installation](../results/runtime13-installation-saved-audit-01/STATUS.md)
- [Standard-library adapter source and 12 focused tests](../results/runtime-std07-source-development-01/STATUS.md)
- [Passed standard-library preparation07 and independent readback](../results/runtime-std07-preparation-01/STATUS.md)
- [Exporter preparation and preserved missing-proof failure](../results/runtime-exporter07-preparation-01/STATUS.md)
- [Closed exporter metadata failure and all 36 successful child commands](../results/runtime-exporter07-metadata-failure-01/STATUS.md)
- [Lossless delayed-load parser and 24 passed controls](../results/runtime-exporter-dyld-parser-test-01/README.md)

Historical plans and source manifests retain their original status text. The
linked actual-result records establish which work has since run; an old plan's
test count is not a new execution result.

- [Successor exporter preparation and held frontend/publication sources](../results/runtime-exporter07-successor02-preparation-01/STATUS.md)

- [Closed metadata and exporter build evidence](../results/runtime-exporter07-metadata-build02-01/STATUS.md)
