The first native prototype passes 358 bytecode library controls in debug and
release, with 12 explicitly ignored diagnostics in each. The closure verifies
314 frozen bindings and four command-output artifacts against `ca3ab2fe`.
These are synthetic unit controls; no original-project benchmark executes.

Subsequent source review found an uncovered ABI boundary: heap-free external
prologues do not initialize guest heap registers x7/x8, but the initial read
emitter always consulted them for tagged addresses. The new fixtures all had
static heap storage. Do not build, benchmark or adopt this revision from the
passing tests. Preserve their exact outcome and add a heap-free emission mode
and boundary/reconstruction control before qualification continues.
