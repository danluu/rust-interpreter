# Native store preparation and compaction qualified

All 378 bytecode tests pass in debug and release (15 ignored) with two test
threads. Address identities are now prepared in one pass over scalar nodes;
each read examines at most 16 prior stores. The compactor recognizes narrow
commit stores and retains their addresses, values and ordering. Full native
memory/budget/alias controls still pass, as does exact arena reconstruction.

Two commands finish successfully. The closure verifies 319 source/retained
bindings and four log artifacts. Production store admission remains test-only,
and no original-project command or timing ran. Next census actual native
eligibility and verify existing adopted scalar bodies byte-for-byte.
