# Local argument-copy proof: coverage before runtime changes

The proof checks every source slot extent in a direct call against the caller frame. It uses only Local definitions in the same basic block, invalidates every register writer, and leaves mixed, indirect, or unproved calls on the general checked copy path. It stores one boolean per bytecode operation.

| Saved production trace | Proven argument copies | Coverage | Proof time | Retained plan bytes |
|---|---:|---:|---:|---:|
| word64-inline8 | 41,427,700 / 42,238,380 | 98.081% | 0.228 ms | 59,089 |
| sha1-inline8 | 18,523,593 / 18,523,998 | 99.998% | 0.079 ms | 18,662 |

Five proof tests and two explicit-result runtime tests pass. Ten fixtures also pass in both engines of the retained VM. They cover overlapping callee slots, zero-sized arguments, overwritten local pointers, caller mutation through references, and error ordering. Out-of-frame source extents stay on the old path: a valid bytecode call can observe the freshly reserved callee storage.

The inspector checks every function name, operation count, and printed operation against the saved profile. Proof times are individual inspector measurements; they are not end-to-end performance results. The initial fixture run had two incorrect expected error messages, corrected to the existing tagged-pointer semantics before the successful run.

The runtime candidate uses safe slice copying for proved calls after the same frame reservation and memory-limit checks. Return handling, instruction counts, language checking, and bytecode version remain unchanged. Performance and full production qualification are pending.

[Candidate validation](../call-local-copy-validation-01.json), [retained baseline](../e2e-engine-specialization-corpus-01/summary.md).
