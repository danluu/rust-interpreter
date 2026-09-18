# Own-thread code append and branch replacement transaction

Extend the existing fixed MAP_JIT arena with one transaction that appends new
words and replaces an ordered set of already committed unconditional branches.
Before writing anything, validate arena capacity, aligned committed patch sites,
strict ordering/no duplicates, expected original branch words, replacement B
encoding and signed targets within the complete transaction extent.

Only after every validation succeeds, toggle this thread's JIT write protection,
copy the staged new words, write the checked branches, restore protection and
invalidate the instruction cache for each changed extent. No allocation,
validation, guest execution or metadata publication occurs in the write window.
Ordinary append delegates with an empty patch batch. Arena addresses stay fixed.

Exercise 64 repeated two-entry updates and immediate native execution, backward
branches and branch-only transactions, stale/malformed/misaligned/out-of-bounds
patches, duplicate/unordered batches, a later stale patch after an earlier valid
patch, and capacity refusal. Rejections must preserve every byte, code length
and both executable results. Check host ABI/SP through the existing wrapper.
Run all 355 bytecode controls in each profile and the two exact saved capture
reconstructions. This qualifies the primitive, not a live demand engine.

The higher-level region publisher must still prove same-function internal targets,
retain bounded pending-edge ownership, reserve all metadata before commit, and
publish stable resume tables/assertion identities after successful code commit.
Its controls must also cover faults, budgets and logical per-PC accounting before
any original guest benchmark or runtime adoption.
