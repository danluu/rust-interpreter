# ReadyHit continuation Python controls

Attempt 02 passed all 14 pure Python controls in 0.030 seconds: six original
upgrade controls, four cold-audit controls and four ReadyHit controls. The
runner, shared engines, tests and checkpoint inputs remained unchanged.
This validates the continuation's Python contracts only. No Rust, native HIR
replay, compiler check, unit-test crate or benchmark ran in these controls or
this archival step.

The tested driver is commit `a5df182dbcda19511b1cc99665796291d2b07046`; its
frozen ReadyHit input is `5cd6acd3f50912cec5fb29375b130afa70506703`, patch
`cca094ebc73f6cc7da9ea1660669a436a6900e5d9c307550435dbcd8784410f4`.
These Python results do not qualify that patch's 26 Rust controls or native
hit behavior. Earlier source and failed/passing predecessor checkpoint inputs
are preserved with their original status.

Both attempts are retained:

- Attempt 01: supervisor 76692 started Python child 76695, which exited 2
  because `.work/hir-ready-hit-upgrade-controls-01/runner.py` did not exist.
  Setup had omitted parent-directory creation. No runner or tests executed;
  the original command and exact error remain in its supervisor log.
- Attempt 02: supervisor 78471 ran helper 78474 and test child 78479, exit 0.
  The canonical workload lock was admitted at `1789325935.7474802`; the result
  was published at `1789325935.880393`. All 33 recorded source hashes were
  checked before and after testing. Raw stdout/stderr, environment, process
  identities and receipts are preserved.

The archive contains every completed test receipt and both supervisors, plus
all exact input bytes recovered only after matching their recorded hashes.
No compiler checkout, target, binary, unrelated process listing or later
source substitution is included.

`evidence.tar.gz`: 48 members, 214,820 bytes, SHA256
`52b92106a1d3f9cc68cf9f7a7710ccbf274ed6df9ee57701558840654027977d`.
Every member was read back and compared with its input. `manifest.json`
records original paths, sizes and hashes; `summary.json` retains the complete
test-input map and separates the failed launcher from the passing tests.

Archive supervisor 3239 ran helper 3242 under the canonical lock from
`1789326032.837953` through completion at `1789326032.8775182`. Its raw
supervision records and their separate hash manifest are included alongside
the archive receipt. READYUP and the compiler source were not modified.
