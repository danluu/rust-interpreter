# Qualification and preparation status

The compact file-table helper passed 29 focused controls and independent audit.
The independent verifier passed 22 additional controls and independent audit;
their complete sources and evidence are in
`../../results/hash-file-table-reader-controls-01/`.

Read-only preparation03 completed successfully with zero workload children.
The resulting table has 109,196 files and 6,770,927,978 declared input bytes:
106,432 unchanged base rows plus 2,764 disjoint additions. All prerequisite
histories, full input guards and provider inventories passed preparation.

The final snapshot projection reserves 51,810,304 bytes against 215,441,408
already allocated evidence bytes. Their sum is 267,251,712 bytes, below the
unchanged 268,435,456-byte limit by 1,183,744 bytes. This includes the original
remaining-stage reserve; it grants no credit for removing or ignoring evidence.
The actual controller must recheck this allocation before execution.

Preparation record SHA-256:
`d0530245c9edeb84309a27258f65d889679f8c38efcb21e2dae5bf6e50c588e9`.
Launch packet SHA-256:
`e315c703101fb5d8e9f732a10db9b07883792057c0f833b71979cf54efcbfc43`.

Final packet review and the three hash workload commands remain pending.
Execution retains the fresh 24 GiB entry requirement. Runtime installation and
application timings remain separate, pending qualifications. No sub-0.5-second
build result is established.

The original source README and copied historical tests remain unchanged. The
newly executed suite here is `test_file_table_audit.py`; this record does not
claim a new run of every historical test file.
