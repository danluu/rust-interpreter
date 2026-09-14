# Qualify bounded aggregate projections before a runtime ABI

Start from exact adopted bytecode sources (7fd1f66f tree, restored by 809fac1c).
Keep the production memory proof and scalar lowering at their original limits.
Test-only entry points allow 1,024-byte frames and 64-byte results, retaining
512 registers/operations, existing scalar argument widths and all work limits.

Compare two memory policies: explicit initialization and the zero bytes of an
ordinary newly entered Call frame followed by ordered captured arguments. Both
still require confined accesses; no external reads/writes, nested Calls, FFI or
arbitrary-entry assumptions. A future private Call ABI must establish all those
preconditions, preserve padding/peak/budgets and handle escaped logical pointers.

First represent the full result as up to four <=16-byte diagnostic projections.
Each projection retains every original bytecode operation, fault root, branch and
PC identity; only its final result slice differs. A projection is never installed
in a guest JIT. Evaluating four bodies is a reference strategy, not a performance
implementation. A future native backend must share computation and return bytes
through one checked Call and one wider private output block.

Eight controls compare every result width 0..64, ordered overlapping arguments,
zero padding, 468 large overlapping copies against an independent byte oracle,
branch joins/full-width conditions, every short budget, dead division and late
faults, external effects, shape/work limits, legacy behavior, local pointer bits
and malformed return annotations. Compare each lane to our ordinary bytecode
interpreter and require identical logical PC counts. Run in debug and release;
also repeat all 13 legacy proof and five scalar-IR controls in release.

After qualification, census actual typed memory and per-lane IR eligibility on
the 132 exact saved candidates. Do not infer eligibility or speed from the prior
10/82 sampled structural observations. Keep production selection unchanged.
Shared lock; build admission max(14 GiB, 8 GiB + twice allocated shared target),
8 GiB child floor, two Cargo workers/test threads. Retain and close every command.
