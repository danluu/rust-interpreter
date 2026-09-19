# Diagnose upper words without full-width consumers

The closed private-frame pairing census covers under1% of either native sample
window and is deferred. The new hypothesis concerns virtual-register storage.
A logical narrow-value proof cannot establish that reused backing bytes are zero.
Instead ask whether any operation ever reads a particular register's high64bits.

Start with typed, whole-function consumer roles: Load/Store addresses, Copy
addresses, CopyDynamic addresses/count, FillBytes address/count/byte, CompareBytes
addresses/count, and Call argument/result addresses explicitly truncate in the
VM. Store payloads consume the upper word only above8bytes. Indirect call handles
always remain full-width because the VM rejects high bits. All unlisted consumer
roles conservatively read both halves, including arithmetic, conditions, switches,
assertions and builtins. Every role, alias and unreachable instruction counts.
Definitions do not establish eligibility. Registers with no read stay unclassified.

Bound registers/PCs at65,536 and visited operands at262,144. Malformed reads or
writes decline the entire function. Six controls cover mixed-role aliases,
unreachable full consumers, indirect handles, nonzero/undefined high contents,
unknown consumers and exhausted bounds. The ignored saved-program observer only
validates/deserializes typed bytecode and emits a list of eligible registers.
It does not compile native code, execute a guest or authorize production omission.

Join those typed identities to actual high-word stores in the two closed current
adopted captures using the already qualified ordinary-memory recognizer. Restrict
to ordinary regions with x0 as the virtual-register base or the exact known x16
large-address recipe; keep scalar bodies and unknown encodings separate. Reuse
the preserved independent assembler object, verify its source/log binding, and
run the six recognizer controls again. Reconcile original samples and distinguish
ambiguous collapsed PCs. Report candidate stores and partial sampled PCs, never
retired instructions, cycles or an end-to-end gain.

Any production proposal needs a separate proof across native/VM boundaries and
reused frames: virtual-register backing is private, consumers must remain safe
with arbitrary ignored high bits, and other functions must initialize any bits
they read. Preserve full-width indirect handles, callbacks, faults, budgets and
all original assertions. No change to checking, initialization or runtime follows
from this diagnostic alone. Keep earlier width packing/paired spill failures.

Hold the root benchmark lock with45-second admission. Reuse only the owned shared
target, two Cargo/test workers, build floor max(14GiB,8GiB+2*target allocation),
12GiB offline admission and8GiB child floors. Preserve the paused goal, peer work
and all successful captures. No new guest run or installed VM is needed.


## Expanded masked integer consumers, census02

The initial closed address/byte proof covers24/10 sampled stores, insufficient
alone. Source review of the actual VM shows binary() masks both inputs and the
shift count for widths<=64; Unary masks before dispatch; Cast uses its source
width before sign extension. Extend only these reviewed widths.128-bit reads,
conditions, assertions, indirect handles, floating-point and builtins stay full.
Retain the initial six controls, add width/alias coverage and3,800 comparisons of
actual binary() results/errors under poisoned high bits, plus signed-source
checks. Eight Rust controls run per profile; six traffic controls remain.
The new typed result must contain every previously eligible register. Use fresh
02 evidence, preserve01, and still do not omit stores or execute any project.
