# Preserved compiler failure

The new CFG proof failed to compile because a block-edge closure parameter lacked an explicit usize type. No tests or profile analysis executed. Add the type annotation; preserve all proof logic, bounds and test assertions. Terminal ownership, sources and compiler diagnostics remain.
