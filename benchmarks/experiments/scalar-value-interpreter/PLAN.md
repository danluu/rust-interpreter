# Scalar interpreter execution milestone

Reuse the integrated VM loop with a const scalar-ABI specialization and borrowed
validated metadata. Preserve the version-5 API and all original workspace tests.
Apply the qualified artifact injection first, then the separate runtime changes.
No new interpreter or external execution backend is introduced.

Root, direct/indirect calls, mixed arguments, returns and TLS callbacks honor
their declared register/frame locations. Register backing is initialized before
ordered argument reads. Scalar result registers start at zero before inputs are
assigned, including when result/input registers alias. The input-aware proof
never exempts other uninitialized reads. Keep memory/depth error order and exact
budgets/profile accounting.

Eight runtime tests compare explicit scalar fixtures with independent memory-ABI
adapters and known arithmetic/lifecycle results. Retain all eight artifact tests
and the complete original workspace suite in debug/release; one original test
remains ignored. Exact original artifacts must still roundtrip unchanged.

This milestone exposes the Artifact interpreter library API only. Scalar JIT
requests fail explicitly until native support exists. No runtime publication,
compiler conversion or timing comparison follows this intermediate milestone.
Complete native resumable support, caller value operands and compiler admission
under the existing scalar-value-abi contract before the fixed real workflow gate.
