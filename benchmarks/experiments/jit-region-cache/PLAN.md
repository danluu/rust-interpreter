# Use idle native registers for short-lived values

The width-packing census found negligible dynamic benefit from adding more
globally assigned values. The current emitter has only two caller-saved local
cache registers (x5/x6), even when some or all of the six persistent registers
x23–x28 are unused by a function. The next candidate makes those unused registers
available to short-lived dynamic facts inside resumable native regions.

Keep the current whole-function assignments, native call convention and bytecode
unchanged. Assigned pairs remain reserved. Extend only the region-local cache
with the unassigned suffix of x23–x28, for at most eight native registers total.
Full u128 values must own two slots with explicit low/high physical registers;
narrow values use one. Preserve alias snapshots, eviction liveness, local-memory
forwarding invalidation and exact VM/budget fallback. Flush facts at the existing
region boundaries. The resumable external prologue already saves all six native
registers; ordinary regions and native trees/stubs retain the old two-slot path.
Use bounded recency metadata and deterministic replacement, preserving the old
two-slot policy when the extra bank is unavailable. Do not add any parked runtime
optimization, change guest limits or weaken checking.

Qualify wide/narrow pressure, overwrite aliases, medium-copy clobbers, loops,
native Calls/Returns, interpreted fallbacks, code-capacity declines, assertion and
budget ordering, and all callee-saved registers. Add deterministic generated
valid-program comparisons with persisted inputs on failure. Run workspace tests
in debug/release and exact-output real saved programs before timing.

Freeze candidate/control identities before a single screen: six balanced token
pairs with recorded/replayed entropy and identical artifact/options, requiring
at least 10% median wall improvement and no CPU regression. Include all VM/JIT
preparation in each command. A failed screen parks this candidate without retiming
or held-out promotion. A passing screen proceeds to actual source-edit/build/test
commands for the expanded token suite, folded and pgrust, then large held-outs and
the private project. Compare against retained anchors in the same session.

Use one active workload, two Cargo workers, bounded 45-second global-lock waits
and an 8 GiB free-space floor before children. Preserve artifacts, executable
tools, raw evidence, private caches and unrelated work. No new storage subsystem.
