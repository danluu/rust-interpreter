# Immutable conditional-demand candidate

Tool `4cdd305b692c6f89fdbe9ce92b006f8f8ba74961c56a66bca66c53b7a1119bcd`
contains VM `54fb895b2c77c4798667efdb81bd9ecfa21399b8a16124e189b6ce0c5e1be88c`.
The exporter and wrapper exactly match adopted tool df4006e0. This candidate
selects program-wide demand preparation only when a function exceeds the
existing 65,536-PC analysis bound; ordinary programs retain eager preparation.

All 640 workspace tests pass in debug and release (15 ignored per profile).
Python discovers 431 tests: 409 pass and 22 skip. Both saved adopted native-code
captures reconstruct exactly. The boundary, full-validation and fixed-owner
controls pass. Six qualification commands are represented: the exact closed
debug command from disk-stopped run 02, with matching runtime/test/build sources,
and five new commands. Total recorded setup is 136.56 seconds; new setup is
65.95 seconds. No guest benchmark or latency claim is included.

Run 01's diagnostic assertion failure and run 02's disk stop remain preserved.
Next qualify strict/cache behavior, original small-program eager profiles and
current-parser demand coverage before a fresh changed-source parser primary.
The experimental runtime is not adopted on main.

[Summary](summary.json), [closure](closure.json).
