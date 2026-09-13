# Production compiler setup through stage1 controls

The owned production compiler source is frozen at actual Git commit
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. Preparation, the explicit formatting
continuation, stage1 compiler/native-stdlib build and stage1 controls passed.
This archive does not qualify stage2, a final installation, interpreter behavior
or build performance.

| Attempt | Outcome | Recorded child commands | Outer supervisor / helper |
| --- | --- | ---: | --- |
| prepare-02 | passed | 11 | 89840 / 89907 |
| freeze-source-01 | failed; retained | 3 | 97396 / 97399 |
| freeze-source-continuation-01 | passed | 24 | 7684 / 7726 |
| stage1-01 | passed | 13 | 22976 / 22984 |
| stage1-controls-01 | passed | 13 | 17003 / 17010 |

Child counts include source/identity Git commands and are not test counts. The
exact build and control commands, results and stdout/stderr remain available
in the archive. Each child receipt is bound to its stage and output hashes; each
stage is bound to its completed outer supervisor. Canonical-lock admission and
completion times remain in their original records.

The first formatting attempt built the bootstrap helper and extracted the
already pinned formatter components, then both `x fmt` commands rejected their
path arguments. The separate continuation used the exact underlying formatter
recipe from pinned bootstrap source, verified its complete archive-derived
extraction and stamp, checked/formatted only the six reviewed source files, and
created the real compiler source commit. It then wrote the original driver's
source/inventory/completion schema. Original plan02, its inputs and the failed
attempt remain unchanged and are retained together with the continuation plan.

The archive includes every original plan02 source input, the one explicitly
pinned external rust-src comparison proof, continuation source and recipe
identities, full frozen source/backtrace inventories, production configuration,
the six final source files and both formatted patch deltas. It does not copy
compiler binaries, formatter archives, sysroots, Cargo targets or other caches.
Recursion was limited to the five explicitly completed stage receipt directories.
Only the listed source files and exact supervisor records were read elsewhere.

`evidence.tar.xz` holds 357 members (10,570,568 compressed bytes), indexed with
exact source path, size and SHA256 in `members.json`. Its SHA256 is
`701af2f37f6878b77a34da8abfa174c29da1eba006574553ea507b3919ffcc3c`.
The builder verified every archived member and rechecked its source bytes.
`summary.json` and `packaging-receipt.json` retain the archive identity and
canonical-lock packaging receipt. The first archive attempt's overly narrow
input-path check rejected the already-pinned external proof before output
creation; that attempt and its corrected successor are both retained.

No compiler, test or benchmark was executed by archival. No frozen driver,
compiler source, prior receipt or observation was changed. Remaining production
driver stages, complete installation, matching tools, strict36, observable57 and
screen27 remain separate required steps. This is setup evidence, not a speedup
or final sub-0.5-second result.
