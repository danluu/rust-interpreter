# Join actual miss costs to saved bytecode differences

Read only the closed actual session trace and closed consecutive artifact-difference
census. Require exact eight artifact hashes/state order and both trace reconstruction
and original outcome closure. For each worker/function, compare the current attempt
with that worker's previous attempt; join every intervening consecutive bytecode
comparison. Classify unchanged body, only immediate values, immediate/call IDs,
function identity movement, or other structural differences. A changed body can
coexist with changed callee/scalar inputs; these categories do not isolate causes
or authorize omission of any identity input. Unchanged-body misses still require
current callee and dynamic admission analysis. Retain first-seen/evicted distinctions.

Sum diagnostic emission intervals only across valid edited requests and retain
all-state subtotals. They overlap across workers and do not estimate command gains.
No guest, native publication, build, cache mutation or runtime policy change.
benchmark.lock45s,12GiB analysis admission,8GiB closure; exact inputs hash-bound.
