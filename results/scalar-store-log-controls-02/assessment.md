# Store-log controls pass

All 381 bytecode tests pass in debug and release, with 17 ignored observers per
profile (762 passed tests across two commands). New controls compare complete
active linear and heap memory after success and errors, covering same-block
write guard reuse, read-only/bounds failures after earlier writes, intervening
partial aliases, and every instruction budget in both register modes.

The earlier preflight-only failure is retained separately. These controls
establish no speedup. Build a new immutable candidate for full workspace,
strict Cargo, original-profile and changed-source primary qualification. Main
still uses df4006e0; the old store candidate remains parked.
