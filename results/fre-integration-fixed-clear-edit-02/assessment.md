# Exact frame clearing improves the real es8 edit command

The five-edit pilot passes its predeclared 8% gate: median paired complete
command wall time improves **9.22%**, and CPU improves **9.33%**. Median times
are 4.226s baseline, 3.839s candidate, 1.506s native and 0.575s Cargo check.
The candidate is still about 2.55 times native on this integration workload.
The result supports further qualification, not promotion or whole-suite claims.

All 32 commands completed. Both VMs execute byte-identical artifacts in every
source state. The two original assertions pass, the deliberately underreported
bound fails in native and both VMs, and Cargo check accepts that well-typed
logic error. Five cumulative equivalent edits change production library code.
The original file is restored exactly, and all four restored commands actually
recompile and pass. Sixteen executed artifacts and all command logs are retained
and hash-verified. Native keeps 18 jobs, repository debug settings, incremental
O0 and default test concurrency; the custom batch is sequential.

Both custom tools use the identical retained exporter and wrapper, paired with
the separately qualified baseline/candidate VMs. Each has its own warmed Cargo
cache. The initial commands primed fresh custom caches and are excluded from
edited medians; their 7.950s/7.372s timings are not a matched cold-build claim.
The first launch (`fre-integration-fixed-clear-edit-01`) stopped at the initial
disk guard before any command or source edit. Its failed receipt remains; the
completed launch uses the same comparison and unchanged thresholds.

Continue with broad native/TLS/real-project correctness and repeated full
command regression gates. Runtime source is `6f9e148`; the paired recipe and
composition receipt are committed in `7ed2d29`. The private experiment branch
remains separate from main until those gates pass.
