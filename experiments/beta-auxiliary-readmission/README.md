This successor passed four metadata controls, one actual 39-command metadata run,
six strip-parser controls, and one 19-command assembly/real-strip run on September
18. The fresh B2 build sysroot and its auxiliary strip tool are qualified for this
bounded control. No exporter rebuild or application performance result is claimed.

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

The separately reviewed assembly copied all 335 files into fresh ordinary inodes.
Both actual auxiliary-tool invocations loaded the intended beta LLVM library.
The debug object shrank from 14,120 to 4,136 bytes: nine DWARF sections disappeared
and all five non-debug section payloads, sizes and flags remained identical.
The source and original object were unchanged. All 334 original B files remain
unchanged. The object was not executed.

The assembly receipts are under `.work/beta-auxiliary-assembly-01`:

- `receipt.json`: `e7ca6e60ba69c5ec2bfd66e7e24d97aa90979441401ccb77e5548dce8502ef94`
- `strip-proof.json`: `c40d917eaabb2fb65621ca8a963aac3b2ac74e49e3fce7266252e2b763470b5b`

The independent verification record is
`.work/beta-auxiliary-assembly-independent-verification-01.json`, SHA-256
`76a2f43d58c35801d5091fba45aa404025d2eb079fbf3d7f10ab80324fa768d7`.
It rehashed all 1,009 frozen source/proof inputs, eleven retained source snapshots,
335 B2 files, 836 proof copies and originals, and 334 original B files, and checked
all 19 raw command associations. The six-control summary is
`.work/b2-strip-controls-01/summary.json`, SHA-256
`ac12405a7ae964642b5af71043e02e61e91d6a0706cd9e71a1e4a0079b0e690a`.

Separate current-platform stock-compiler controls, a fresh exporter build bound
to the installed runtime, and application qualification remain required.
