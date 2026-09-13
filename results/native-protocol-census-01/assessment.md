# Current native protocol attribution

Both saved unprofiled captures reconstruct exactly: 1,101/1,305 complete
functions and 4,183/4,932 native Call/Return transitions. Their operation maps,
assertion counts, transition bytes and resume entries match. The test-only
labels partition every transition byte. Debug and release each pass 402 bytecode
tests, including two new partition controls; six tests are intentionally ignored.
Two explicit offline reconstructions and one attribution command pass with zero
guest executions or executable-code publications.

| Captured generated self-PC samples | Block | Exhaustive |
| --- | ---: | ---: |
| All generated instructions | 1,651 | 1,439 |
| Complete Call/Return transitions | 433 | 499 |
| Frame clearing, including its address setup | 110 | 100 |
| Argument source addressing/checks | 60 | 53 |
| Frame publication | 41 | 51 |
| Argument and result copying | 19 | 101 |
| Return dispatch | 35 | 31 |
| Return destination addressing/checks | 25 | 25 |
| Unassigned finer transition samples | 0 | 0 |

Frame clearing is 6.66%/6.95% of generated samples. Exact opcode-sequence
matching further identifies 34/39 samples in the existing 64-byte clearing
loop and 13/89 in ABI byte-copy loops. The exhaustive copy samples split into
57 at 136-byte transfers and 32 at 304-byte transfers. These are actual loop-PC
samples, not the number of copied bytes or the cost of the entire caller.
The remaining clear/copy samples stay explicitly classified as other code;
they include fixed clears, setup and tails. No sample is assigned by function
name alone. No new sample or profile execution was needed.

Proceed with a bounded composition: wider exact frame clearing, pair-at-a-time
large ABI memmove, and the previously qualified paired private-register transfers
where their current-source diff remains compatible. Preserve all initialized
bytes, complete checks, ordered argument copies, overlap semantics and fault
ordering. The old argument-only and whole-frame initialization-elision proofs
had insufficient coverage and remain parked. The prior paired-register timing
alone did not pass; it is not independently adopted or retimed here.

These are partial perturbed windows under ordinary entropy. Static instruction
counts and sample shares are diagnostic, not speedup estimates. Require fresh
strict/original-test qualification, a primary-first 40-command screen with A/A,
and every full adoption guard if the screen passes. The current 16 MiB default,
strict frontend and original assertions remain in force.

[Full attribution](attribution.json), [exact loop refinement](loop-parts.json),
[build qualification](../native-protocol-build-01/summary.json),
[next composition](../../benchmarks/experiments/native-boundary-memory/PLAN.md).
