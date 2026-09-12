Cargo publication qualification passes 19 commands on the qualified scalar
compiler/runtime aa56492e. It is installed under that explicit immutable key;
normal source selection remains the production compiler.

Five invocations of the same owned Cargo target select versions 5, 6, 6, 5, 6.
Each version reproduces its earlier exact artifact hash. The launcher records
the scalar option and checks the selected artifact header before execution.
A deliberately mismatched cached sidecar rejects before VM execution and is
restored exactly. Uncalled type/borrow errors also prevent stale execution;
the source is restored and runs again.

Original fixture assertions pass native Cargo and both custom artifact versions.
Version-5 and version-6 allocation traces bind to their selected artifact hashes.
Both audit packs retain the correct versions and their original assertion bodies
execute. Two hash-consistent reports with wrong artifact versions are rejected.

These are correctness checks, including cache invalidation. No unchanged-build
performance claim is made. The launcher changes are separately frozen in
benchmarks/experiments/scalar-value-cargo/launcher.py. Fresh original-workload
qualification and the fixed complete-command performance histories follow.
