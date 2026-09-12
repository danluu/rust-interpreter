The isolated scalar interpreter passes 305 debug and 305 release workspace tests (one ignored). Eight new runtime tests cover all scalar widths, aliased input/result registers, direct and indirect mixed calls, recursion, reused backing storage, TLS callbacks, ordered faults, and exact instruction budgets. Eight artifact-format tests and both original version-5 artifact roundtrips also pass.

Scalar formal arguments and results use a validated version-6 ABI table. Caller operands still supply addresses; complete caller value operands and compiler promotion remain required. The old Program APIs reject version 6 so metadata cannot be lost silently. Native scalar execution is explicitly rejected in this milestone.

The build is isolated and unpublished. These are correctness checks, with no real-workload scalar timing or speedup claim. Source, test outputs and process ownership are recorded in [summary.json](summary.json) and [execution.json](execution.json).
