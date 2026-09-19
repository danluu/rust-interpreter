# Historical retained proof copies

This is an unrun source proposal. It validates metadata for an explicit subset
of proof copies whose complete bytes already exist in qualified, still-live v2
gzip snapshots. It does not read files, load a controller, decompress, retire
files, grant allocation credit, or claim an old inode still exists.

`references.build(...)` takes the complete original logical file table, the
fresh current physical table, the closed owner's full retained-inputs manifest,
the explicitly approved copy names, required-live names, and a previously
qualified complete snapshot catalog. The owner and catalog callbacks must each
return exactly `True` after their independent role-specific authentication.
Callbacks receive copies and cannot mutate the authenticated comparison inputs.

Each historical path must be a non-executable, single-link ordinary proof copy
directly under the explicitly bound retention root. Its original row, the
retention entry, the still-current original source, and the qualified gzip's
logical descriptor must agree on SHA and length. All unselected original rows
remain current with unchanged full identities. Every physical catalog blob
must also be a current ordinary input, and all evidence roots stay counted.
Selection follows the already-qualified catalog order. Multiple logical copies
may share one physical witness without earning any additional physical credit.

`partition(saved_references, **complete_build_context)` reruns `build`, including
both authentication callbacks, and demands complete typed equality before it
returns separate current and historical portions of the ORIGINAL table. Their
typed union equals that original table. Extra fresh current sources are already
validated by `build` but are not returned as part of the old table's partition;
its `current_physical_files` count includes them. The fixture tests this
distinction. A fabricated proof cannot bypass owner, scope or required-live
checks by calling `partition` alone. Raw SHA and full gzip EOF still remain
caller obligations. Ordinary `file()`, `identity()` and `file_record()`
APIs continue to reject an absent historical copy. No virtual path is exposed.

The proposed first use is 21 copies under the closed run-make WORK's `retained`
directory. The original 61-entry retained-inputs manifest remains unchanged.
All 21 are delta-only rows in the completed hash-stage03 table, are absent from
all existing snapshot logical selections and metadata03 live inputs, and have
qualified gzip witnesses already counted by driver02. Their original sources,
compiler/provider/SDK/config/application inputs, selected logical snapshot
inputs, and physical gzip payloads all remain live. The original completed
stage03 packet and audit remain historical evidence; they are not described as
rerunnable against removed paths.

Before retirement, the integration must authenticate the passed retention
owner, its original manifest and archive audit, the passed hash02 owner, every
physical witness and its complete gzip/logical EOF, and the exact old copy bytes.
The runtime reader then verifies the new current-or-historical partition and
rebuilds the full continued catalog without recursion. Current-live Stage guards
and the existing file-table, v2 snapshot, and completed-catalog helpers stay
unchanged. The new representation, source and control evidence are retained as
new logical inputs under unchanged caps.

The source fixtures cover accepted partition/aliases and invalid scope,
retention/owner associations, typed counters/identities, selected/live inputs,
ordinary current source and physical witness changes, catalog path/inode
duplicates, callback mutation, and fabricated retirement/allocation credit.
They use tiny in-memory metadata with explicit fake authentication callbacks;
they do not claim to qualify gzip I/O or an actual retention owner.

No actual cleanup is authorized by these files. It still requires reviewed
source, bounded controls, exact full recovery proof, completed successor reader
qualification, no active consumers of the copied paths, and a separately
reviewed qualified-fd retirement with independent durable-ledger audit. Only a
fresh complete allocation sample after that action may count reclaimed space.
The future runtime's new gzip reservation remains unmeasured.
