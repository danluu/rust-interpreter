# Cargo integration-test target selection

The unfiltered fre command exposed 52 integration tests in ten Cargo targets
outside the existing library-only replay. Extend the launcher with explicit
`--test-body --test-target NAME`, use Cargo's `--test NAME`, and bind artifact
selection to that exact target kind/name. Preserve default library behavior,
strict rustc type/borrow checking and the retained exporter/VM binaries.

Source lives under scripts/ on branch experiment/test-targets. The small
experiment launcher loads that source against the existing installed tools;
it does not rewrite or inject source. First check an isolated Cargo package
with a library and two integration targets whose same-named entry functions
have different assertion outcomes. Verify A succeeds, B fails, A succeeds,
then prove wrong production code and uncalled type/borrow errors do not execute
stale bytecode. No LLVM guest engine, disabled assertions or lazy borrow checks.

Then qualify original fre integration assertions on a fresh explicitly recorded
Cargo target/cache. A target-selection fixture is correctness evidence only;
real edit-to-test commands must guide any latency claim. Keep the original
unfiltered native doc-test diagnostic failure visible.
