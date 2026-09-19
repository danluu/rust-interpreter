# Complete workspace qualification

All628 Rust tests pass in debug and release, with15 declared ignored diagnostic
observers per profile. Python discovers449 tests:427 pass and22 skip. The four
recorded commands complete normally against source d7de70da, supervisor91817 /
child91860. These include the9new native/VM representation controls and the
existing native scalar transaction, memory, frame, budget and ABI suites.

The isolated tool is
`3e53b127220f71115eec7b18e2ed452577471ab48cfd5d4c669c0ae3a295f32a`,
with VM SHA256
`8e369c0f3a6f6fd0b793372d27c26f4848db8536f4cb8bfcf8672b0d0a12ca72`.
Exporter cf4b3499 and wrapper45bca4f2 are unchanged from adopted df4006e0.
Only this isolated composition is installed; main's adopted runtime is unchanged.

The111.4seconds of setup include all tests and the VM build. No original project
guest or latency benchmark ran here. Next require121strict/cache commands and
three exact current-host original profiles before the40-command primary.
