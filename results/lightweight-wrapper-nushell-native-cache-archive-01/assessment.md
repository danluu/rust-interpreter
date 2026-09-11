# Preserve the complete repeated Nushell native cache

The completed native target of `lightweight-wrapper-nushell-repeated-01` is
archived after verifying all 23,875 unique payloads. Its 140,547 original paths
were retired only after full decoding/hash checks, rechecking the originals
and verifying that no file was open. Original command/source records and all
90 executed bytecode snapshots remain in place and verify.

Unique input is 10,762,597,149 bytes; the archive contains
2,954,415,567 bytes (2.75 GiB). Observed free space
rose from 13,055,561,728 to 20,973,793,280 bytes
(7.37 GiB). Shared APFS activity
means this observation is not an isolated physical-allocation measurement.

Supervisor 58619 and worker 58631 finished with status 0. The [summary](summary.json)
records the inventory, source hashes, all evidence and archive SHA-256
`d3ae0d47ac9061a4ceb029e7117edcb582d853491122ef6b1ed997ccf94ad1ac`. The original preflight observation
of insufficient space is preserved; application began after two separately
verified check-cache archives made sufficient room. This maintenance is outside
all benchmark timings. No tool, source edit, benchmark flag or timing gate changed.
