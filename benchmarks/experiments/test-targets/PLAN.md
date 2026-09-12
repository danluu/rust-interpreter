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

Shared-cache qualification: keep all integration targets for one package under
one Cargo dependency cache. Cargo separates their metadata units; the launcher
still binds execution to target kind/name and serializes selection/publication.
A/B/A and strict-error fixture checks must verify one shared cache and distinct
sidecars; the existing library cache stays unchanged.

Real qualification runs all ten fre integration targets (52 original assertions)
with 18 jobs, native default threads and O0/incremental. Custom batches use the
retained std-MIR/inlining/resumable/persistent settings, a 100B instruction limit
per target and 150K live allocations. Retain every executed artifact using APFS
COW copies. This is original-source coverage; follow it with real production
edits before making latency claims. The initial cache is admitted from measured
historical size; later targets require at least 128MiB above the 8GiB floor.
Report pending targets if admission stops; never silently omit them.
