# Locate the remaining token execution cost

The persistent exporter-cache screen saved 5.30% of complete edited commands,
below its predeclared 8% gate. Its historical VM spent about 3.1 s executing
the test. Do not rerun that candidate or its conditional promotion holdouts.

First compare the historical 21d1e163 VM with the already-qualified 7e4ae256
VM from build ae0a49e. The latter's `crates/bytecode` source is identical to
the current source; it is the baseline of the fixed-clear integration build,
not the parked fixed-clear candidate. Preserve exact binary hashes. The
exporter-only SHA dependency change does not justify rebuilding this VM for
an attribution question.

Use the saved original-assertion token production edit (6e30e327 bytecode),
the two independently recorded and qualified entropy tapes, one excluded
warmup pair and six balanced measured JIT pairs. Require exact stdout,
instruction and peak-memory counts, complete entropy consumption, and input
hashes before and after. Both modes use resumable calls and persistent
registers. Serialize under the existing lock, wait at most 45 seconds, and
require 8 GiB free. This is saved-program runtime diagnosis, not an edited
command measurement, a candidate adoption gate, or a retiming of the failed
exporter experiment. Report all pairs, including regressions.

Then sample three fresh owned current-VM executions with emitted-code maps.
Profile runs are excluded from latency estimates. Attribute samples to guest
instructions and runtime services before choosing a structural change. Keep
all bounds, instruction/allocation limits, frame initialization, TLS and
failure ordering intact. A subsequent implementation requires its own
predeclared end-to-end screen and native controls.
