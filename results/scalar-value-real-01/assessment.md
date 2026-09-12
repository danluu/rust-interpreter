Both original real test batches pass on the existing version-5 artifacts and
fresh compiler-generated version-6 artifacts, using the same qualified custom
VM. Four commands complete; source remains at the pinned fre revision with all
original assertions unchanged. Both runs use actual resumable native calls and
persistent registers. No JIT functions or scalar proofs decline.

| Workload | Scalar formal inputs | Scalar results | Value call sites | Value operands | Value destinations |
| --- | ---: | ---: | ---: | ---: | ---: |
| Folded trie | 1,056 | 135 | 981 | 1,449 | 187 |
| Token phrase | 5,120 | 1,236 | 4,835 | 6,216 | 1,382 |

Folded executes 3,962,595,068 bytecode operations versus 4,138,403,285 on the
original artifact, with identical native call/return counts. Token executes
12,020,254,325 versus 13,345,211,525 in these two observations; its real entropy
remains enabled, so operation differences are descriptive. Frame extents and
required initialization remain; no frame-memory saving is claimed.

Tool aa56492e192ef2e87f69ed417b34c8f717b28c31a0fa67f5d63fbb92f313c9cd;
launcher benchmarks/experiments/scalar-value-cargo/launcher.py. Compiler proof
work is bounded and reported (1,152,065 folded; 5,070,978 token).

This is original-assertion qualification, not a timed comparison. Fresh
three-cycle/five-edit A/A and candidate histories, matched checking/native
controls and the fixed 10% token/5% folded gates are still required.
