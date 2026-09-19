# Complete workspace qualification without replaying passed work

The closed short-clear-tail-workspace-01 prefix executed Python and debug
successfully, then its controller rejected the debug count. Its expected 615
was incorrect: heap qualification had four added tests and six copied tests in
its reference module. The adopted baseline has 608 tests, so this candidate has
609 passed and 13 ignored. Preserve the original incorrect plan and failure.

Before continuing, verify the closed prefix's terminal, source hashes, commands,
child identities, complete logs, 468 Python checks (446 passed/22 skipped), and
609 debug tests (13 ignored), including the four named native contracts. Bind
these results into this continuation. Do not repeat either successful command.

Execute only full workspace release tests (609 passed/13 ignored) and the release
VM build. Snapshot the resulting VM. Reuse the explicitly owned bounded target,
with a 3 GiB allocation cap and max(14 GiB, 8 GiB + 2*allocated) free admission
before and after each child. Keep two Cargo jobs and two test threads, locked
offline dependencies, shared benchmark lock with 45-second admission, and all
original source/proof bindings. Never touch the protected compiler target.

Record combined prefix/continuation setup wall and child CPU separately from
performance. Independent closure verifies both prefix and new evidence. No
original project execution, timing claim, tool-default change or adoption here.
Next qualify original guests and strict checks with an explicit candidate tool,
then run the prospective ES8 primary before held-out project guards.
