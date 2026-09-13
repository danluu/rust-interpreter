# Production compiler completion evidence

The owned compiler at actual source commit
`58e1e1f5311f4424ea81def4763081f6da62d9b3` passed stage2 build, focused
compiler controls, distribution, package composition, native execution and strip
controls. This evidence covers the compiler package. It does not qualify the
interpreter integration or establish a performance improvement.

| Control | Observed result |
| --- | --- |
| Option dependency hash | 1 passed, 17 filtered |
| CGU partitioning suite | 15 passed, 33 filtered |
| Stable module and per-MonoItem run-make controls | 2 passed, 528 filtered |
| Native binary histories | 15 states, 30 commands passed |
| Native binary and proc-macro strip controls | 6 variants, 15 commands passed |

The native histories preserve edited and restored source, actual compiler argv,
stdout/stderr, CGU reuse reports and recorded binary hashes. The strip controls
cover `none`, `debuginfo` and `symbols` for both a native binary and a proc-macro
library, including execution of the resulting consumer. Both controls use the
explicit per-MonoItem policy with stable-module grouping disabled. Their package
guards report all 6,902 package files unchanged.

The production profile has assertions and overflow checks disabled in the
compiler and native standard library. It uses the reviewed bootstrap source
remapping, exact pinned CI LLVM and its `rust-objcopy` support executable. The
package retains both the original stage2 build inventory and the later qualified
inventory, including the additional test-built `rustdoc`. The native raw E0080
source/snippet probe passed; its receipt explicitly leaves full diagnostic
presentation and interpreter qualification to subsequent gates.

`evidence.tar.xz` contains the eight completed stage receipts, every recorded
child receipt and stdout/stderr, all eight outer supervisor plans/status/logs,
all direct package metadata and probe logs, and the direct native/strip control
source and logs. It also contains plan02, its 112 exact frozen input files, final
source/configuration and LLVM proofs, both patch deltas, source inventories and
the complete twelve-stage receipt chain. Archive member names, original paths,
sizes and SHA256 values are in `members.json`; `summary.json` records the archive
identity and exact qualification counts. `packaging-receipt.json` and
`initial-summary.json` record the first canonical-lock archive and verification.
`compression-receipt.json` records a second canonical-lock pass using a larger
xz dictionary, which preserves all uncompressed archive bytes and verifies every
member and original source again. The initial compressed archive is retained
privately at the path in that receipt; only the smaller final archive is published.
`compression-runner.py` retains the exact recompression procedure.

The earlier setup, failed original formatting attempt, explicit continuation,
stage1 build and stage1 controls remain in
[the prior archive](../mono-production-bootstrap-through-stage1-01/README.md).
Its archive SHA256 is
`701af2f37f6878b77a34da8abfa174c29da1eba006574553ea507b3919ffcc3c`.
This archive retains the prior summary, packaging receipt and small stage
receipts, and verifies that existing archive's bytes without duplicating it.

Archival runs no compiler, tests or benchmarks. It reads only the listed owned
evidence and source inputs, verifies every archived member, and rechecks all
source hashes before reporting success. Compiler/native binaries, full source
copies, target directories and caches are excluded; their existing inventories
and recorded hashes are retained.
