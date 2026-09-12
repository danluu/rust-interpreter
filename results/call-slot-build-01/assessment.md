# Guarded Call argument VM qualification

Isolated tool `ac38fa59` passes 297 workspace tests in both debug and release,
with one ignored diagnostic. Eight new tests cover bounded slot analysis,
arbitrary initialized entry registers, checked-address equivalence, partial
argument copies, exact budgets/profiles, large register offsets, recursion,
fallback, return faults and the host ABI.

The VM is `af5dd300`. Exporter `556776f6` and wrapper `ba366dd3` are copied
unchanged from integrated control `9637b0ac`. Root Rust sources remain unchanged.
The x22 budget experiment is not included.

Known nonempty argument slots receive a runtime equality guard. Only an actual
address equal to the expected in-frame address takes the direct path; otherwise
the original checked path runs at the same point. Static extents are checked
again by the emitter. Charge points, clearing, copy order, return checks and
all persistent register pairs remain.

The guard uses x11 for the actual address and x12 for the expected address.
Both are original argument-copy scratch registers. Large register loads may
use x16; the callee entry is reloaded at the existing final dispatch. x21/x22,
the host cursor and x23–x28 remain untouched by the guard. The slow path keeps
the original checked-address clobbers. No address facts enter general register
state and no host pointer is retained across VM re-entry.

This is correctness qualification, not a speed result. Original-artifact smoke,
fresh A/A controls and the fixed complete edited-command comparisons come next.
Broader native/TLS/fre qualification and seven held-outs gate adoption after a
successful primary result.
