# Full-width repair census

Seven commands pass:11 controls in each Rust profile and one typed observer.
The new roles cover aliases, width bounds, checked/unreviewed helpers and96
poisoned heap-input comparisons against actual interpreter execution. No
original project guest or native code publication is performed.

Both candidate and adopted current-host profiles have identical interpreted-PC
arrays and typed operations. Their all-read totals reconcile with the closed
conservative census. The full-read classification remains conservative for
TLS, descriptors, C allocators, environment, floats and other unreviewed helpers.

| Test | All narrow reads | Required full-width narrow reads | Affected interpreted instructions |
|---|---:|---:|---:|
| block |6,542,145|1,033,563|1,033,563|
| exhaustive |8,513,802|843,810|843,810|

About84%/90% of repairs can be avoided. Remaining reads are1,025,947/843,776
indirect handles and7,616/34 switch values. Allocation/deallocation/reallocation
sizes and pointers, ordinary Call addresses and indirect argument/destination
addresses already truncate before use. Those paths need no extra normalization.
These are operand counts, not cycles or a causal explanation of the failed
conservative primary.

This admits one prospective selective-repair variant. Keep indirect handles,
TLS width checks, full truth/selection and unknown helpers protected. Native
storage, emitted code, all initialization and frontend checking stay unchanged
from the conservative prototype. Require full qualification and a new primary
against the adopted runtime; do not retime the parked version unchanged.

Source330ac583, supervisor26333/child26336, completes normally. Closure verifies
234 frozen inputs and224Git bindings. No successful profile was repeated.
