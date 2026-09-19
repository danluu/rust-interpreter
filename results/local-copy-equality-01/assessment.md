The bounded copy-equality model passes14 controls and independently closes with
52 verified bindings and both full derivations recomputed (supervisor75783).

It finds2925/3374 static copy sites but covers only26/7 generated self samples:
1.35%/0.49% of the block/exhaustive windows. Cyclic sites contribute19/4 samples.
Fixed-entropy logical copy executions are78,800,895/59,486,163, a separate count
stream. These observations are not eliminated instructions or a speedup bound.

Do not build or time this narrow redundancy pass alone. The next mechanism to
assess is retaining memory-copy payloads independently of the volatile x9 scratch
register. Existing small-copy emission still loads/stores through memory after
scratch clobbers. A reserved SIMD payload cache could avoid selected source loads
without changing committed guest bytes, but needs actual load-PC coverage,
register-clobber review and typed/native proof before implementation. This differs
from the previously rejected larger virtual-register cache and scratch-width
extension. No runtime change has been selected yet.
