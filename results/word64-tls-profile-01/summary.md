# Word64 profile after TLS qualification

The exact artifact passed all twelve original word64 tests in the production-edit corpus. This run records execution counts, not benchmark timings.

| Remaining VM operation | Executions |
|---|---:|
| Call | 39,144,083 |
| Return | 39,144,084 |
| Jump | 25,822,090 |
| Local | 15,018,145 |
| Binary:Add | 10,479,044 |
| Binary:Mul | 4,077,967 |
| Binary:Sub | 1,183,234 |
| Binary:Div | 3,443,660 |
| Binary:Rem | 920,367 |
| Copy | 6,869,823 |
| Assert | 6,286,955 |

Next experiment: emit checked add/subtract/multiply and their overflow booleans directly for widths up to 64 bits. Keep arithmetic and overflow checks intact. Verify boundaries, output/source register aliasing, and native Rust behavior, then compare the exact artifact with alternating VM builds before rerunning edit workflows.

Inlining is deferred: frame/register growth can undo the register-initialization gain. Historical forwarding-wrapper triage covers only about 2.15 million calls, fewer than the remaining checked arithmetic operations.

Artifact SHA-256: `807f04b6528ce5f5de6dc37b4ec450212f55747041e8053d54f750f7135c6e6a`. Baseline tool: `9708df423e8c5d0e3cc8cebb55779f28aa4466096fef35617a15a9d7f1d09fc9`. Raw: `.work/word64-tls-profile-01`.
