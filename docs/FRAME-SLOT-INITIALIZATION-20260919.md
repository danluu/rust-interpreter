# Pointer-slot initialization proof: parked after coverage measurement

The bounded extension passes18 controls in each debug/release profile, including
6,400 independent CFG byte-mask cases and19,584 concrete overlapping-copy cases.
It tracks exact eight-byte pointer/literal cells, invalidates overlapping or
unknown writes, and intersects facts at joins. The adopted runtime is unchanged.
The original constants proof reproduces every previous result on the same saved
artifact. Among5,468 functions, initialized eligibility increases1,150→1,152;
confined effects increase669→671. No previously eligible function is lost.
[Build and controls](../results/frame-initialization-slots-build-01/summary.json).

The new proof establishes no additional sampled clearing coverage on the adopted
runtime. Exact function/Call-PC joins reconcile66,403,971 and70,368,276 logical
Calls, separately from the two original partial normal-entropy sample windows.

| Adopted capture | Generated samples | Frame-clear samples | Previous proof | Slot extension |
| --- | ---: | ---: | ---: | ---: |
| Block |1,561|89|1|1|
| Exhaustive |1,231|62|1|1|

Ignoring caller-argument restrictions does not increase either sample ceiling.
Together the two newly eligible functions add only2,687 logical Calls in the
block profile and11 in the exhaustive profile and no frame-clear samples. These are diagnostic bounds,
not latency measurements. The earlier historical16/110 and20/100 counts came
from an older runtime and must not be presented as current coverage.
[Exact coverage](../results/frame-initialization-slot-coverage-01/summary.json),
[independent closure](../results/frame-initialization-slot-coverage-01/closure.json).

Park this mechanism without a production pass or performance screen. Do not raise
proof limits or retry the unchanged analysis to manufacture scope. The remaining
unknown-pointer/effect declines are different proof obligations, not evidence that
whole-frame clearing can safely be removed. Padding, address guards and arbitrary
native-entry states remain unresolved runtime obligations.

The next distinct review concerns local writes fully overwritten before a read
or possible fault in the same native region. Unlike equality or payload caching,
this asks whether temporary bytes need to be stored at all. Its first stage must
be a conservative saved-evidence scope model with a concrete memory oracle; it
must preserve memory at every read, fault barrier and exit before a typed runtime
implementation is considered.
