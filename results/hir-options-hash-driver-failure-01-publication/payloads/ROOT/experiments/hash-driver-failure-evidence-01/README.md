# Closed failed-driver evidence

This is an unexecuted archive source proposal. It retains the original driver01
compiler failure as a failure: one compiler invocation exited 1 and neither
planned driver process ran. The separate read-only failure audit passed.

The exact proposal is O `.work/hash-driver-failure-retention-proposal-01.json`,
SHA-256 `8a3b56f5dd8d52e12e14389bba3771fea32c3d06cf3b2b4b5348330aeebafe13`.
It selects 168 ordinary files containing 40,467,639 bytes. These include the
complete failed WORK, all 65 newly stored snapshot gzip files, the prepared
stage02 packet and sources, preparation03 history, terminal/launcher/raw
evidence, failure-audit source and execution, and the exact two-edit driver-v2
derivation. Descriptions of driver-v2 as uncompiled refer to the proposal's
historical observation; this archive does not execute it.

`archive.py` checks all selected identities and bytes before and after writing,
checks closed-directory membership, verifies the actual failure-audit
association, and writes deterministic ordinary GNU-tar members through gzip9
with timestamp zero. It then independently reads every archive member and the
gzip trailer. Source files, provider files, previous archives and Git remain
unchanged. Partial archives and failure receipts are retained on any refusal.

The 34 reused gzip blobs and the original native03 file-table base remain
explicit references to their two already published archives. The proposal,
manifest and summary record exact archive SHA-256/Git blob IDs, logical and
physical member paths, alias chains, member hashes, and prior independent
archive audits. This action rechecks those selected manifests and audits; it
does not reread or duplicate the old archive payloads. Recovering the full
transitive proof requires those referenced archives as well as this one.

Bounds remain 256 selected files, 64 MiB per selected file, 128 MiB selected
logical bytes, 32 MiB compressed output, 132 MiB expanded archive, 2 MiB per
generated document, and 1 GiB total reads. Compressed fit is not yet measured.
The wrapper requires 9 GiB plus a 64 MiB output reservation before creating
evidence and again after obtaining the canonical lock. It waits at most 600
seconds for that lock. The archive child has 300 CPU seconds and a checked
600-second wall bound; the parent explicitly observes for at most 650 seconds.
The live disk floor is 9 GiB. No timeout signals or retries are implemented.

`execute.py` is a narrow successor of the passed failure-audit wrapper; its
adjacent diff records the namespace, bounds, source pins and closed-result
association changes. It retains the exact engine, proposal, ownership helper,
execution source, raw output, PID, parent, argv, cwd, environment and times.
There are no identity-probe subprocesses. Its single child processes the
archive; it starts zero compiler, provider or driver workloads.

Expected outputs are ROOT `.work/hash-driver-failure-retention-execution-01`,
`.work/hash-driver-failure-evidence-01`, and
`results/hir-options-hash-driver-failure-01`. The result directory contains the
exact proposal, manifest, archive and summary. The source proposal does not
authorize running the wrapper. A separate review and actual archive audit
remain required before publication.
