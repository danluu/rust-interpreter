# Live region preparation passes its first controls

Explicit demand-region execution passes all 369 bytecode tests in both debug
and release (13 ignored per profile), including seven live differential
controls. Both saved eager captures still reconstruct exactly: 11,313,812 and
13,757,056 bytes across 43,439 ordinary regions. The four setup commands took
70.44 seconds; these are correctness/setup results, not performance evidence.

The live controls cover cold regions, loops, instruction-budget tails, guarded
memory fallback, calls/returns, scalar composition, prepared reuse after
failures, forced plan/metadata refusal, TLS reset and nested callbacks. They
compare values, original per-PC logical counts and peak guest memory against
interpreter and eager execution. Code, plan and metadata admission stay bounded.

Source is 213e4882c11d5a93571e512303cb2d0f364444ed. The closed receipt verifies
324 source/input bindings and ten artifacts. No original-project guest command
or changed-source timing ran. Runtime changes remain experimental. Next add
interleaved-region diagnostics, expose the explicit mode, and qualify complete
workspace/strict controls and original-project profiles before screening speed.
