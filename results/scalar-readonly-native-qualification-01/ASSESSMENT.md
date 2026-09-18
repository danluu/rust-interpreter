# Strict qualification passed; performance remains unmeasured

The separately keyed read-only native-Call candidate passes all 121 qualification
commands. Native, reference-interpreter and custom-JIT fixture results agree,
including reused bytecode. Actual partial-demand artifacts and uncalled type and
borrow errors are rejected with scalar Calls enabled. Valid changes invalidate
the appropriate cached output and restoring the source restores its artifact.
Automatic-cache behavior with incremental compilation disabled also passes.

The supervisor finished with status zero. Closure verifies the expected negative
outcomes, all command logs and 17 frozen source/retained bindings. This is the
candidate built from 66aec1c8, tool cb47107b9d64; the exporter and wrapper match
the adopted df4006e0 tool. Its preceding build passed 622 workspace tests per
profile and 407 Python tests, with 22 declared Python skips.

Next run the three original diagnostic workload profiles against the exact
retained adopted-VM profiles, then the fresh 40-command changed-source primary
screen. Both candidate and current control enable scalar Calls. These fixture
and cache checks establish no compilation or end-to-end performance improvement.
