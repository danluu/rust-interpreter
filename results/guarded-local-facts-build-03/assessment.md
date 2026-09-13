The three-part local-fact/scalar-copy candidate passes 504 workspace tests in
each of debug and release; three explicitly ignored offline observers remain
separate. The build verifies all 180 frozen inputs and installs VM `f0e5f2ea`
as composition `317a0bf1`, retaining the exact qualified b08f39e2 exporter and
wrapper. Source is `faaf9074`.

Both earlier failures are retained. Build 01 exposed incorrect new-fixture
address assumptions and an old test that no longer represented an unknown
pointer after full-width local-pointer forwarding. Build 02 exposed a JIT-only
option incorrectly passed to the interpreter reference. The corrected tests
retain opaque pointers, partial overlaps, exact byte comparisons and finite
instruction budgets. Direct-emitter tests now enable the production paths.

This establishes workspace correctness coverage, not real-project qualification
or performance. Next run the frozen 119 strict/cache controls and three exact
real-test profiles before the prospective changed-source token screen.
