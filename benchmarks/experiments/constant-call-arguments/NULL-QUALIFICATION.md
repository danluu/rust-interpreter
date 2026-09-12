# Qualify the null-read fix in a complete tool build

The two new boundary regressions reproduce the original defect and pass after
the two scalar-data transfer rules reject address zero. All 18 constant-analysis
tests pass in debug and release in constant-null-analyses-01. Qualify the full
workspace and rebuild the exporter before the corrected folder is eligible for
any production-source screen: expect 368 passed tests and one ignored per
profile, then all bytecode/exporter binaries. Preserve every original tool and
the null-failure artifacts. The old compose02 tool stays disqualified.

Host qualification floor: 4 GiB. This is an explicit small-rebuild exception,
not a fresh Cargo-project admission. Reuse the same already populated debug and
release host cache used by build08 and the just-completed 18-test checks. Those
checks ended with 5.598 GiB free; their release rebuild changed free space by
less than 1 MiB. Dependencies and both complete host profiles already exist;
the Rust change is two transfer guards and their regression tests. Full checks
may relink consumers, so retain a 4 GiB floor before every child, record actual
free space around each stage and stop normally if it is crossed. No source or
artifact retirement, download or new target tree is part of this build.

The build driver keeps its 8 GiB default. Selecting 4 requires both an explicit
frozen plan and existing debug/release dependency directories. This exception
does not change the actual token screen's 6.5 GiB admission or 4 GiB reserve,
nor any other real-project admission. It enables complete correctness checks
for the already isolated fix without another cache-retirement cycle.

Build09 stopped before Cargo because its cache admission check incorrectly
expected the legacy deps/ layout. The pinned Cargo uses build/<crate>/<hash>/out;
build10 checks for existing rlibs in both profile build trees. Preserve the
preflight failure; it contains no compiled or executed test.

After build10 passes, compose03 retains the exact baseline VM, saved03 repeats
the three complete-artifact transforms/verifications, and fixture02 repeats the
18 native/custom commands over nine standalone tests and uncalled type/borrow
errors. These stages also use the 4 GiB reserve. Composition/saved diagnostics
write only tool copies and small artifacts; fixture01's entire native cache was
under 4 MiB and its project has no dependencies. No large project cache is made.
If saved03 produces the exact previously replayed bytes, carry the 34-test replay
through explicit digest bindings instead of repeating its timing.
