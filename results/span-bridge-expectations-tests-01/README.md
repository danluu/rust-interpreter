# Four Python bridge-expectation controls passed

All four `test_expectations.py` controls passed in 0.002 seconds, with exit 0.
These exercise synthetic event histories and expected-output validation only.
No Rust, native bridge, proc-macro fixture, compiler build or benchmark ran.
They do not qualify the span-handle implementation or establish a speedup.

The tested fixture bytes are exactly commit
`c964a9e0bb128372f28f41bd78a72bba1b42d007`, present unchanged in clean integration
checkout `eaf3d93c498aa02ecb52a107b4b247335748e9f4`. The original span patch
remains SHA256 `05aeea42bf6e3cd3aa9c1ec3adfdad65e6846e11e0419dca5490b253c4a922ff`.
All 14 bound inputs were checked before and after the command, including the
full fixture, patch, original source review, supervisor and runner. The test
environment contains only the recorded HOME/PATH/locale and Python isolation
settings; bytecode writes and user-site imports were disabled.

The canonical workload lock was held from admission at `1789325663.877878`
through result publication at `1789325664.1595252`. Owned supervisor 9561 ran
helper 9564 and test child 9581. Exact commands, identities, environment,
stdout/stderr, source snapshots and before/after proof are retained.

`evidence.tar.gz` contains 25 files, 29,627 compressed bytes, SHA256
`b1722f95587b5370dc59bada729b07ab82f87aa002dad21d53f419e2cbcafc33`.
The archive was produced under the canonical lock and every member was
independently read back and compared byte-for-byte with its input.
`manifest.json` records every member's size and hash; `summary.json` preserves
the original test summary, and `archive-receipt.json` records archive ownership.

The unchanged source README and source-review receipt inside the archive retain
their historical unrun status. This result qualifies only the four Python
expectation controls; all described real bridge/native histories remain unrun.
