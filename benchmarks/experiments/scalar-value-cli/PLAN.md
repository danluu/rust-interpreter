# Scalar interpreter CLI qualification

Copy the exact qualified scalar interpreter source into a new owned tree. Change
only the CLI loader/dispatch and add a fixture writer. Preserve version-5 loading
and execution routes; version 6 uses its explicit Artifact methods. Legacy JIT
remains available. Scalar JIT must fail explicitly until native support exists.

Build the CLI and fixture writer with two jobs, locked/offline, under the shared
benchmark lock. Run serialized version-5/version-6 addition fixtures against a
fresh pinned native Rust executable, including u64 wraparound. Check ordinary and
profiled results, exact scalar instruction budgets, malformed artifacts and JIT
rejection. Bind all sources, artifacts, commands and outputs. These are process
integration checks, not performance measurements or real-workflow speed claims.

The underlying library already passes 305 debug/release tests. This step does not
repeat that unchanged suite. No experimental tool is published as the normal
compiler; native scalar support, caller value operands and compiler promotion
remain required under the existing ABI contract.
