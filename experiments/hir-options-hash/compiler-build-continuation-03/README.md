# Source-correct support-library continuation (unrun)

The first continuation built E2 and passed all eighteen interface tests. Its
seventh command failed because pinned bootstrap has no `build` registration for
`src/tools/run-make-support`. The saved failure remains unchanged. The exact
registered `test::CrateRunMakeSupport` route uses compiler0 and
`Mode::ToolBootstrap`, builds the support library, and runs its fifteen unit
tests plus ordinary doctests. It does not run the run-make recipe.

This successor executes exactly three commands: that support-library test route
and the two original final Git guards. Twenty-two earlier successful commands
are replayed from raw evidence. The failed unsupported route is retained as a
separate actual row. The resulting logical successful history has twenty-five
commands; the full actual history has twenty-six, with three controller owners.
No completed compiler or test command is repeated.

`support_source.py` binds bootstrap dispatch, compiler role, all support Rust
source, fifteen definitions (including six expected panics), and three doctest
fences: one executable example and two explicitly ignored illustrative examples.
The actual non-test lib/dylib Rustc command and its output directory are retained
separately from internal ToolBuild metadata. Bootstrap's JSON renderer prints
plain unit names; six expected-panic annotations remain in the source proof.
All printed Cargo contexts are classified with complete timing stacks; dry-run
self-check prints are retained, and every plausible real context must yield the
same full effective D2 ToolBootstrap environment for the exact two-shim producer.
Output discovery requires actual
rlib, rmeta and dylib bytes from that producer.

The canonical lock remains 600 seconds, with 24 GiB entry, 9 GiB stop, 8 GiB
floor, 14 GiB namespace and 256 MiB aggregate evidence bounds. The monitor sums
all three completed compiler histories plus this successor. Its process-control
logic is unchanged from the passed thirteen mocked controls. Missing exact
process observations still refuse signaling.

The preparer is unrun. It will bind the complete current build/expanded-registry
membership after any separately reviewed cache-retirement transition. Historical
snapshots are retained as historical admission observations. No compiler source,
native runtime, application source or option is changed. Native recipe, B3,
hash-driver, application and performance qualification remain separate.
