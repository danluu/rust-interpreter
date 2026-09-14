# Native runtime installer synthetic qualification

All **13 controls passed**, with no skips, on source
`bd2ca6830bae54bda6c636b44d5316094f78e00a`. Raw unittest stderr reports
`Ran 13 tests in 0.273s` and `OK`. These tests use tiny synthetic files and mocked
compiler/loader probes; no real compiler sysroot, compiler-source checkout or compiler archive was
read by the control workload, and no native/application qualification is claimed.

- Actual supervisor/helper/test: **46637 / 46640 / 46642**.
- Canonical admission: **1789344515.779358–1789344516.1693618**.
- Frozen input manifest: `744f2c8d6731af4284cfd1dcd241f87f958e9f8851fbcdbdc49515b5513108a3`.
- Raw command receipt: `85b73709f8e6454e640db85910a2e1e119b71958ffa23f461876222f1cc17b23`.
- Raw stderr: `0924bbb495d0b1d5047bc6626cf5ca87de02cc45fc887d497b4a8f5c9f25d254`.

`evidence.tar.gz` contains 21 exact source/control/launch/supervisor files plus
its manifest. All eight frozen source snapshots are included. `manifest.json`
maps original absolute paths to archive members, hashes and byte lengths.
Every member was read back and checked after compression; the archive SHA-256 is
`d43d08d0f0887192ef2f8bb6f5112f6806ce726948f063bd073cb9dca03b7446`
(28,565 bytes).

Archival itself ran under the canonical lock, supervisor/helper **72468 / 72471**,
at **1789344670.082129–1789344670.0906072**. `archive.py` and
`archive-inputs.json` retain its exact helper and inputs. `execution/` contains
the archive launch, admission and completed outer supervisor receipts;
`archive-execution.json` binds their bytes after terminal completion.

The source README was updated after the tested original README had been archived.
The runtime module and test source remain byte-identical to the tested checkpoint.
Stage2 loading and launcher/std/tool publication were not changed.
