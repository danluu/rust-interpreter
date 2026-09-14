# Incorrect partial-artifact fixture expectation

The environment fixture passed native, interpreter, ordinary JIT and reused
bytecode checks. An added scalar rejection assertion then failed because this
artifact was fully checked: unsupported-call traps are independent of demand
frontend checking. Its successful scalar execution was correct.

The next run enables scalar mode on these fully checked legacy fixtures and
exports a genuinely partial artifact with the existing demand frontend option
for the negative control. No Rust runtime source/binary changes were needed.
