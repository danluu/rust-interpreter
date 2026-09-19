# Selective interpreter repair diagnostic

The conservative implicit-zero runtime3e53b127 failed its primary wall gate.
Do not repeat it or start larger guards. Its sources and immutable tool remain
retained. This diagnostic changes only test code and executes no original
project guest. Main stays on the adopted runtime; no selective repair exists yet.

Classify read roles against the actual VM dispatch. Pointer/length/heap operands
cast to usize, fill values cast to u8, store payloads at most8bytes, direct Call
addresses, masked integer inputs and casts from at most64bits do not consume
upper bits. Indirect handles stay full. Full truth/selection,128-bit operations,
TLS width validation, C allocators, descriptors, environment and unreviewed
helpers stay conservative. Aliased roles still count separately.

Four new controls cover aliases, checked/unreviewed helpers, width bounds and
actual interpreter Allocate/Reallocate/Deallocate behavior with poisoned high
input/pointer bits across48 size/alignment combinations and two poisons. Run
four unchanged width-proof controls and three cost/shape controls as well:11
controls per profile, followed by one ignored typed observer. No native code is
published. Synthetic interpreter fixtures are distinct from project commands.

Bind both candidate and adopted current-host profiles from the closed original
comparison; verify identical interpreted-PC arrays and exact typed operations.
Reconcile all-op counts with the closed conservative census. Report necessary
and unique full-width reads, affected instruction counts and opcode breakdowns.
These remain work counts, not elapsed time or a causal explanation of the failed
primary. Unknown roles stay full; no scalar hits become interpreted work.

Use the root lock with45-second admission, two Cargo/test workers and the owned
shared target. Build admission is max(14GiB,8GiB+2*allocated target), every child
requires8GiB. Preserve all completed evidence, peers and the paused goal.
