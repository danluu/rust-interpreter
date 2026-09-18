# Scalar local-register candidate: correctness qualified, timing pending

593 workspace tests pass in each debug/release profile (11 ignored). The
17 focused scalar native body/Call controls also pass in both profiles.
The new three tests compare allocated code with the spilled native reference
and scalar oracle through register pressure, branch merges, 128-bit results,
nonmonotonic CFG order and every budget/fault boundary in the fixtures.

The explicit original-artifact census preserves all478 previously eligible
scalar functions and reconstructs all71 observed old scalar native bodies
byte for byte. It publishes no executable code and runs no guest. Across
these478 statically emitted bodies, stack loads/stores change1914/1821 to
508/575; summed per-function scratch sizes change14080 to3616 bytes. These
are static sums, not simultaneous memory usage, dynamic hardware instructions
or speedups. In copy_nonoverlapping's precondition function, stack accesses
change69/61 to12/20 and scratch416 to96 bytes; machine-code size stays2816.

Tool `dbf0e067e83fcbebd744f2de53acaef213e2f8af451c46e67dc4d6199f38bbb4`,
VM `aa498c5d332ae1019311798811a69cedd6f645f8a5f0f56f1c4e54dbe11091cb`,
source `93cf6c15990d9b1247baa74456206e4547472b25`. Strict compiler/exporter and
matched adopted control remain unchanged. Five setup/qualification commands
cost118.85s; the separate cached emission census command costs0.245s.
The closure verifies448 frozen source/evidence inputs and all child logs,
including the census and reference manifests.

Strict/cache commands, exact original-test profiles, prospective edited-source
screen and full multi-project/parser comparisons remain required. No runtime
adoption or performance conclusion follows from this receipt.
