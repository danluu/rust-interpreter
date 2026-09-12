# Checked test discovery qualification

The Cargo launcher can now list built-in libtest names and attributes through
`--test-body --list-tests`, using the fully checked compiler context. It does not
need a native test executable and does not lower or execute guest bytecode.
Names come from compiler descriptors, including feature/cfg and target selection.
Canonical names take precedence over ambiguous short-name fallbacks.

All 325 Rust tests pass in each profile (one ignored), as do 44 Python tests.
The generated Cargo fixture passes 25 commands: native name comparisons, root
and nested execution, ignored/expected-panic attributes, a Result test, feature
transitions, an integration target, source additions/removal/restoration, and an
empty target. Both native and custom checking reject an unused borrow error;
a custom test framework is rejected explicitly. A side-effect sentinel confirms
that listing never invokes test bodies.

Six real-project commands compare fresh listings from retained original-source
native binaries with compiler discovery. Pgrust's hashfn has four matching names;
fre-kernels has 389, including the same seven ignored tests. Raw plans freeze the
source pins, native executable hashes, restoration receipts, tool binaries and
selected metadata sidecars. Sources and existing evidence remain intact.

This qualifies discovery, not a performance gain or full harness execution.
Automatic filtering should happen inside the same checked compiler invocation
that exports selected bodies, avoiding an extra frontend pass in the edit loop.
Single and empty selections, the execution bound, and unsupported expected-panic
semantics must be handled explicitly in that next change.
