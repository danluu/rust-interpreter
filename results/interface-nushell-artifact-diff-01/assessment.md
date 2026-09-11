# Nushell's cache-history difference is in constants/data

A freshly built typed diagnostic decoded and validated the cycle-zero and
cycle-one artifacts for all three source states from the repeated API edit.
Original-source and wrong-edit pairs each have 453 functions, unchanged
function headers and instruction counts, 415 immediate-value changes across
115 functions, and no other opcode-field changes. Readonly data grows from
10,720 to 10,736 bytes. Mutable statics and TLS descriptors are identical.

The generic-edit pair is byte-identical: 455 functions, 10,768 readonly bytes,
no changed functions or operations. This also checks the diagnostic against
an unchanged pair from the same run.

The changed constants/data are consistent with a different allocation or
relocation layout, but that is neither an established cause nor an equivalence
proof. Immediate values can contain integers, pointers or packed values.
No addresses were normalized and no artifact was replaced. The passing selected
tests do not justify a cache key that ignores these differences.

[Build command, source/binary hashes and three comparisons](summary.json)
