All 119 qualification commands pass for composition `317a0bf1`. Native,
interpreter, ordinary JIT and resumable JIT controls agree within the fixture
coverage. Cold and warm function-cache exports preserve bytecode, the real
helper edit changes the expected result, and restoration reproduces it.
Automatic-cache controls pass with incremental compilation enabled and disabled.
Uncalled type and borrow errors remain rejected before guest execution.

The exact qualified b08f39e2 compiler and wrapper are retained. These are
correctness controls; no build-time or end-to-end speedup is claimed.
