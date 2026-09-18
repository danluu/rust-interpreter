# Native stores pass complete bytecode controls

All 377 bytecode tests pass in debug and release (15 ignored), including native
store execution, complete memory comparisons, contained and uncertain overlap,
branched effects, faults after non-idempotent mutation, fresh-frame exclusion,
heap-free ABI, register lifetimes, result aliases and exact arena reconstruction.
Both persistent-register settings are exercised. The first compile failure is
retained separately. Production store admission remains closed behind a scoped
test hook. No original-project command or performance comparison ran.

Before the native census, bound address-identity preparation to one linear pass
and teach dead-register elimination to retain the new narrow store encodings.
The current fallback correctly preserves those bodies but skips compaction on
an unrecognized encoding. Qualify these changes in a separately named run.
