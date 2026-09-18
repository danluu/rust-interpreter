# Error-message oracle mismatch

Four of seven native bridge tests passed in debug, including private failure
replay, escaping addresses, complete result/profile/peak comparisons and exact
shared-arena reconstruction. Three failed because the new oracle required the
interpreter's memory-error wording. The adopted JIT already combines bounds and
readonly errors as `JIT guest memory access failed`.

The correction requires exact agreement with the adopted JIT's error, while
allowing only those two known interpreter Memory wordings. It retains exact
interpreter agreement for all other errors, instruction totals, values, peaks
and per-PC profiles. No emitter change follows from this test failure. The
failed source and terminal/log evidence remain immutable. Release did not run.
