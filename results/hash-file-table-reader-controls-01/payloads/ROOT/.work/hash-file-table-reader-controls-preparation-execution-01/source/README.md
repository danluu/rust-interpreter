# Independent compact file-table reader controls

This separate 22-test suite compares the independent stage02 verifier reader with the qualified generic file-table split/expand contract using only tiny task-owned temporary fixtures. Synthetic /fixture file-table rows are metadata and are never opened. It covers complete roundtrip and current-header preservation, exact base binding, disjoint membership, typed metadata and integrity, malformed base JSON, nested references, symlink routes, and mutation during reading or after reconstruction begins.

The run/prepare/child harness is derived from frozen-file-table-delta-controls-01. Its audit hook and resource policy are unchanged: canonical exclusion with a 600-second wait, 16 GiB entry / 9 GiB live / 8 GiB floor, one pure test child, 120-second alarm, 60 CPU seconds, 256 KiB per written file, 256 writable names, 2048 directories, and 2 MiB retained stage output. No compiler, provider, process-control, or network calls are permitted by the child audit policy.

Preparation selects only stage02 verify.py, test_file_table_audit.py and README, the generic file_table.py and README, this harness, and the existing runner/tool closure. It does not import stage02 stage.py or prepare.py. The fresh WORK is .work/hash-file-table-reader-controls-01; the independent audit target is .work/hash-file-table-reader-controls-independent-verification-01.json.

These sources are unexecuted. A prepared packet requires separate exact review before the single control launch. Prior 29-control helper qualification is separate from this reader suite.
