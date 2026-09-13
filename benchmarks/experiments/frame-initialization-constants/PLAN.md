# Recognize explicit constant memory operations in the initialization diagnostic

The first CFG/callee-effect census is retained unchanged in
`frame-initialization-cfg`: zero of 110 / 100 clearing samples are covered. Its
decline review found constant-sized FillBytes operations initializing local
aggregate slots and local addresses formed with constant offsets. This separate
source extends operand coverage; no runtime, compiler or artifact is changed.

Keep the previous CFG/interprocedural proof, bounds and entry contract. A register
fact is either an exact literal or a frame-relative Local offset. Carry only
identical facts across joins and kill every output using the complete visitor.
Permit unsigned 64-bit Local-plus-literal addition only when the target-width
offset stays within the allocated frame. Honor result/overflow alias ordering.
Do not infer pointer facts through loads, arbitrary arithmetic or casts.

For literal extents representable as usize, treat FillBytes as a write,
CopyDynamic as a read followed by a write, and CompareBytes as two reads.
Require the same exact initialized ranges and confinement conditions as their
fixed-size equivalents. Unknown sizes keep the conservative effect rule. No
symbol-name specialization or assumptions about Rust's unsafe preconditions.

Run the original eight controls and 6,400-case oracle plus two focused controls
for constant offsets, width/overflow aliases, constant memory extents, overlap
and unknown size. Analyze the same saved artifact and join the same native Call
IDs and sampled PCs. All previous results and the initial missing-module compile
failure remain evidence. Coverage remains an upper bound: caller address guards,
padding, terminal faults and exact runtime qualification still precede elision.

Keep 45-second shared-lock admission, two Cargo workers, 16 GiB before builds,
12 GiB before the saved join and 8 GiB before each child. Record exact sources,
build/setup costs and terminal outcomes. Preserve other sessions and the paused
goal; do not change the cleaner, use subagents or activate AWS services.
