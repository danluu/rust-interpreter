# The changed constant history contains another copy of a panic literal

Read-only inspection of the six preserved artifacts narrows the earlier
[structural difference](../interface-nushell-artifact-diff-01/assessment.md).
The pinned Nushell source contains `panic!("Expected OneOf")` in three test
branches, at lines 523, 539 and 554. The literal is fourteen bytes long.

| Source state | Literal occurrences, cycle zero | Cycle one | Readonly bytes, zero → one |
| --- | ---: | ---: | ---: |
| Original | 1 | 2 | 10,720 → 10,736 |
| Wrong edit | 1 | 2 | 10,720 → 10,736 |
| Generic API edit | 2 | 2 | 10,768 → 10,768 |

Counts search the complete serialized file; their file offsets are not guest
addresses. The earlier typed report independently shows that the first changed
readonly bytes, at offset 368, spell the new literal. For original and wrong
states, function 3, `test_oneof_deduplicates`, has one reported immediate change
at instruction 122. Splitting its value numerically into low/high 64-bit halves
gives `(224, 14)` before and `(368, 14)` after. The other 377 immediate changes
present in the report's bounded prefixes have a low-half delta of sixteen.
The original report counted 415 changed operations; these prefixes contain
only 378, so this is not a census of every changed immediate.

These observations support investigating changed sharing of this literal's
allocation. They do not establish why rustc supplies a different allocation
history or prove that every changed immediate is a pointer. The API-edit
artifacts remain byte-identical; all original artifact hashes verify.

The exporter's `allocations: HashMap<AllocId, usize>` is used through lookups
and insertions. It is not iterated to determine allocation order. Materialization
appends storage on the first request for an ID, with at least sixteen-byte
alignment. Thus replacing that map with an ordered map would not address the
observed mechanism. The next diagnostic should trace allocation requests and
reuse at the three literal references, preserving their originating function,
constant and relocation edges. A changed compiler allocation-sharing decision
is a hypothesis to test, not a deduplication rule.

This inspection executed no compiler or guest code, changed no artifact/cache,
and read source from the recorded Git revision rather than the live benchmark
checkout. It does not alter the concurrent wrapper benchmark or any retention
criterion. Bytecode reuse still needs explicit identities, relocations and
aliasing rules; equal bytes alone are insufficient.

[Reproducible inspection](../../benchmarks/experiments/artifact-diff/inspect_literal_history.py)
· [Inputs, hashes and observations](summary.json)
