# Bind cache archival to completed compiler commands

The cache-selection helper passes 31 rejection checks and nine read-only
historical verifications: check/baseline/candidate targets from the lightweight
Nushell qualification, the repeated pgrust wrapper comparison and the older
repeated Nushell interface comparison. These cover both standard-MIR and
ordinary-library builds, and old/current launcher recordings.

Each custom target is independently reconstructed from the manifest, package,
test-body selection, standard-MIR key, tool key and run/mode namespace. Every
recorded executed artifact must lie inside that target. Its preserved snapshot
must remain outside the retired cache, match the launch receipt's size/hash,
and pass the existing full workflow verifier. Checks must name the exact
separate `check` target. Original source controls, terminal ownership and all
paired artifact checks are retained.

Rejections cover private/foreign sources, namespace sharing or omission,
different tool/standard-library identities, changed or missing launch traces,
foreign artifact locations, missing or altered snapshots, foreign check
targets, and missing modes. An owned fixture verifies that a busy launcher
invocation lock refuses archival, a released lock succeeds, and a symlink lock
is refused. No compiler cache is modified by these checks.

The [summary](summary.json) records each derived target and the exact helper
sources. Supervisor 4293 and worker 4300 completed with status 0. Archive
write/verify/retirement behavior is qualified separately by the archive fixture
suite; this test does not time a build or establish storage savings.
