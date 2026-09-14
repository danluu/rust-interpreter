# Cross-block allocation has narrow scope on the adopted scalar backend

Four model controls pass in both debug and release, including 256 diamond
fixtures with an independent forward register-identity oracle. All 137 scalar
bodies in the three adopted profiles reconstruct byte for byte (60/69/8).
The census has no allocation declines and publishes no machine code. Its three
commands take 20.84 seconds; closure verifies 261 frozen bindings.
The first attempt's module-path build failure is separately closed.

| Successful scalar IR occurrences | Block before → after | Exhaustive before → after |
| --- | ---: | ---: |
| Spilled definitions | 9,051,572 → 449,072 | 23,824,768 → 0 |
| Spilled non-phi operand reads | 52,107,080 → 43,504,580 | 142,948,808 → 119,124,040 |

Only one function selects the model's global assignment:
`std::ptr::copy_nonoverlapping::precondition_check`, with 43 assigned narrow
values instead of 41. It keeps the same four physical registers and leaves
phis in stack slots. Folded changes no assignment and has no counted spills.
These are successful IR occurrences, excluding phi-edge transfers and failed
private attempts; they are not native instruction counts or predicted savings.

The separately closed unprofiled operation-attribution reports assign 23 of
1,561 generated block samples and 113 of 1,231 exhaustive samples to this whole
scalar body. The proposed two-value improvement touches only part of that body.
The critical block test therefore has limited observed scope for this mechanism;
partial samples are not a proof of its maximum possible effect.

Keep this as a qualified test model and defer emitter integration/timing. The
earlier 245-body spill census belongs to the parked store-log prototype, while
this adopted-runtime census has 137 bodies; do not transfer those larger counts
onto main. Investigate the store-log architecture's overhead and whether a
provable entry guard can admit useful direct effects without rollback or replay
after a committed store. Any such change needs a separate contract and model
before native execution and a fresh real-edit gate.
