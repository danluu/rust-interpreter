# Miri failure: do not adopt version 03

The native nine-test Arena run passed, but the subsequent Stacked Borrows run
failed in `retained_disjoint_mutable_strings_survive_shared_growth`.
Its saved diagnostic identifies `grow`'s `last_chunk.len()` at arena.rs:85 as
creating a shared slice over the previous chunk and invalidating a live mutable
string. Seven earlier tests passed before that failure; Tree Borrows did not
run in this attempt. The full raw evidence remains in
`../../results/proc-macro-arena-miri-04/`.

That growth expression is byte-identical to the original source. A focused
original-code control is pending, so this observation does not establish how
the original implementation behaves under that control. The native pass does
not override the Miri failure. Do not adopt version 03.

All existing version 03 files and results remain unchanged. The separate,
unrun `../proc-macro-arena-reuse-04` proposal records current chunk capacity in
`Cell<usize>` and reads that metadata during growth instead of borrowing old
allocation bytes. It still needs independent review and execution.
