# Null-read constant facts

The old folder converted a nonempty load at address zero from an invalid-memory
fault to a successful zero value. The offline argument census likewise claimed
bytes from data padding at a null argument address. Both regressions fail before
the fix and pass after it. The failing artifact pair remains in the owned raw
before-run directory.

Both transfer functions now reject zero before reading the immutable data range.
Valid nonzero data reads retain their previous behavior. The folder boundary
regression covers five load widths, valid starts, the end of data and usize::MAX;
it also checks interpreter/JIT behavior and exact per-artifact instruction limits.
All 18 constant-analysis tests pass in debug and release. This focused library
qualification publishes no new compiler/VM tool. The offline census fix can ship
independently; the folder still needs a newly qualified tool before benchmarking.
