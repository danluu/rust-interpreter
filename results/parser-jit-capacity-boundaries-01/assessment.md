# Explicit capacity correctness and mechanism checks

All 16 commands passed: eight invalid VM invocations, rejection of an old VM
before Cargo starts, four small-fixture capacity controls, and three complete
114-test parser runs. These are saved-artifact correctness checks, not timings.

| Parser configuration | Original tests passed | Maximum observed owner code bytes | Maximum owner compilation declines |
| --- | ---: | ---: | ---: |
| Default 16 MiB | 114 | 16,383,656 | 1 |
| Explicit 16 MiB | 114 | 16,127,476 | 1 |
| Explicit 32 MiB | 114 | 32,835,736 | 0 |

The larger configuration publishes code beyond the previous bound and removes
the decline. Two prepared workers compile according to their assigned tests;
their accumulated code totals need not match between separate suite runs.
These totals do not establish a default-versus-explicit performance difference.

The small environment fixture preserves exactly the original native output and
34,287 logical instructions at default, zero, 16 MiB and 32 MiB capacities. Zero
capacity publishes no native code. The other three configurations each publish
452,980 bytes. Invalid values, duplicate or missing arguments, an interpreter
engine with an explicit JIT limit, and extra capability arguments are rejected
before an artifact can load. The launcher rejects an older VM before Cargo.

The exact prototype VM is
`b40eb7ff30199393ab223cead8428474feab8fe0c4a3f99960d263b4eb89d648`,
in immutable tool `c0378f22956270c76f4ef8ab6237612f3f68715cdcf9a9a9b7ff24b8accd860b`.
The independent 119-command strict qualification and both 497-test Rust profiles
already pass. The default remains 16 MiB; the next decision requires complete
changed-source measurements with the same VM at both explicit limits.

The supervisor completed with exit 0 on September 13, 2026; PID 453 supervised
driver PID 456. Its log hash is
`46fd45240fb2d19851b4d2508d4fd189b9d8028d1a495e42b40635a9f7d6e51d`.
The [summary](summary.json) binds the frozen plan, command records and suite
receipts. Original parser assertions were unchanged.
