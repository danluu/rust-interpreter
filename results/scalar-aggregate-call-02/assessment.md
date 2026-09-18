# Six controls pass; the positive heap fixture used a null source

All full result/error/memory comparisons passed, but the heap control's final
commit-count assertion failed: it requested a successful Call with source exactly
HEAP_POINTER_TAG. Both the ordinary VM and JIT reject heap-relative offset zero
as null, so the observed zero commits were correct.

Use TAG+1 for the positive case and the destination-boundary sweep, retain TAG
as an explicit negative source, and assert ordinary execution succeeds before
requiring the positive native commit. This also ensures that the destination
sweep reaches its intended Return checks. No production change is needed.

The debug run passed six controls and failed this fixture; release/full-library
commands did not run. Source f81f674b and complete diagnostics are closed.
[Closure](closure.json).
