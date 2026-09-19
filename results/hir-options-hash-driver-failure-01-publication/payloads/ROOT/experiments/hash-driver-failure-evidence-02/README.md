# Failed-driver archive: explicit macOS startup environment

Source02 is an unexecuted successor to the retained archive01 refusal. The
archive-processing child exited 1 before creating its WORK, result directory,
or compressed archive because macOS added `__CF_USER_TEXT_ENCODING` to the
explicit environment passed by the wrapper. The original source01, execution
record, raw output, and source capsule remain unchanged.

A separate read-only Python startup diagnostic observed exactly one addition:
`__CF_USER_TEXT_ENCODING=0x1F5:0x0:0x52`. No passed value changed or disappeared.
Source02 requires the full observed environment to equal the fixed passed
environment plus that exact addition. It records both environments and the
addition separately; arbitrary extra environment variables remain rejected.

The original proposal SHA-256 remains
`8a3b56f5dd8d52e12e14389bba3771fea32c3d06cf3b2b4b5348330aeebafe13`.
The tar archive still selects exactly the same 168 files and 40,467,639 bytes.
All source identities, failed compiler history, 65 stored gzip files, 34
external archive member associations, native03 base reference, finite limits,
and full member/gzip EOF checks remain in force. The original compiler failed;
the archive does not qualify it or invoke a compiler/provider/driver.

This source uses fresh execution namespaces ending in `-02`. The original
proposal's WORK `.work/hash-driver-failure-evidence-01` and result
`results/hir-options-hash-driver-failure-01` are reused only after checking
that neither was created. The exact proposal retains its original source01
route as history; the current executable must resolve to source02.

The additional generated `previous-attempt.json` retains all ten immutable
failure and diagnostic files (292,377 original bytes) losslessly as UTF-8,
alongside hashes and identities. This small document is separate from the
unchanged 168-member archive. It records the missing first attempt release
timestamp honestly. The failed child did finish; no timestamp is invented.

`execute.py` retains the same canonical 600-second lock wait, fresh 9 GiB plus
64 MiB reserve, 9 GiB live floor, explicit 650-second observation, no signals
and no retry. The engine keeps 300 CPU seconds, a checked 600-second wall
bound, 32 MiB compressed and 132 MiB expanded caps, and 2 MiB generated-document
caps. Compressed fit remains unmeasured.

The independent `verify.py` and `execute_verify.py` are source-only successors.
They bind actual receipt, execution-record and summary digests only after a
passed archive closure, verify both environment observations, read the full
first-failure capsule, and independently hash all 168 sources and tar members
through bounded gzip EOF. Their unchanged canonical admission is 16/9/8,
180 CPU seconds, 300 seconds for reads and 350 seconds for observation.
No source02 import, archive execution or verifier execution has occurred.

Each Python file has an adjacent exact `.from-01.diff`. Separate review is
required before any source02 execution. Archive and audit publication remain
pending.
