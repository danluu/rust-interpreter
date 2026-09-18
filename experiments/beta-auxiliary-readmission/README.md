This metadata successor passed four synthetic controls and one actual 39-command
run on September 18. It prepares a fresh B2 build sysroot plan; it has not assembled
that sysroot, stripped an object, rebuilt an exporter, or measured application
performance.

The September 13 launch remains unrun. Its source and proof bytes still match,
but it cannot run unchanged: all recorded device identifiers changed from
16777231 to 16777229, the host changed from Darwin 25.6.0 to Darwin 27.0.0, and
the OS-owned xcode-select, xcrun and otool executables changed. Xcode, SDK, clang
and linker selection stayed the same; clang's default target text changed with
the host. The old identities and qualifications remain historical records.

The successor admits current records only after hashing the complete historical
payloads. All 2,498 historical input records stay intact. Device-only changes
require every other identity field and all bytes to match. The three changed OS
executables have explicit new hashes and identities. The passed E readmission
provides a separate current runtime predecessor and exact current snapshot.

The actual run repeated full source, native runtime, original B334, loader and
SDK guards. Its 39 raw command records retain exact argv, environment, cwd,
PID/parent/time associations and stdout/stderr. It retained 44 metadata source
snapshots and verified all 817 frozen source/proof inputs. Its admission kept
the canonical lock, 600-second wait and 16/9/8 GiB capacity gates.

The resulting composition has 335 files, 1,055,383,020 payload bytes, the original
256 private inputs, and 836 proof copies totaling 129,937,857 bytes. Its sole
payload addition to B334 is the original beta LLVM library at the target-library
path used by the beta auxiliary tool. Historical composition identities were not
rewritten; the new plan contains newly verified current records.

The completed local receipts are under `.work/beta-auxiliary-readmission-01`:

- `receipt.json`: `d7a399cb3b0ed74dd30387f56f94ba8ffe84d9b35aa368dd24d31b3ad2c9d505`
- `planned.json`: `3e1eb36ff072d13227377f4e69ce6d738c37ddeb81d51c865a2c69546060bb5b`
- `current-inputs.json`: `3bac163f21aa0c3b00c130661adf156467632cb5b1ae115e0ea5c8ad4916f7ab`

The independent verification record is
`.work/beta-auxiliary-readmission-independent-verification-01.json`, SHA-256
`0e71b8daadbf3aa1941ecd93972fc20d6bf95074625ab1071d3b40a766e55e22`.
The four-control summary is `.work/b2-readmission-controls-01/summary.json`,
SHA-256 `a5bd4b244fa3bc1bc40079db222a89b70f04749c9590cb841590faa59a5a3e29`.

Assembly and real debug-object strip qualification require their own reviewed
controller and explicit launch. The plan retains the separate stock-compiler
controls and fresh exporter rebuild requirements; metadata success does not
establish either of those results.
