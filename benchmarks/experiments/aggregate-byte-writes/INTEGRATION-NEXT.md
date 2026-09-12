# Integrate the qualified aggregate-frame compiler

The budget-register VM fails its fixed primary gate and stays parked. Its
roughly one-percent paired changes lie within the matched A/A envelopes.
No additional budget variants or held-outs are planned for that candidate.

The aggregate-frame compiler `9637b0ac` already passed its primary comparison,
broad execution qualification and all seven held-out guards. Make that exact
compiler reproducible from ordinary checked-in sources before opening another
runtime experiment. Keep all frame initialization, limits and runtime defaults.

First build all three ordinary tool binaries from the immutable qualified
compiler source into a fresh target. The original experiment copied VM/wrapper
bytes from its parent; do not assume a normal source rebuild reproduces those
components. Compare every component against the qualified installed hashes and
record differences as an integration blocker, not a runtime speed result.
Never overwrite the installed measured tool with a different binary.

If components match, copy only the exact qualified source differences into the
working compiler, verify that the source fingerprint is `9637b0ac`, and commit
them. Run the normal workspace checks and a fresh normal root build. Require
the same component hashes before connecting the ordinary launcher/source index
to the integrated compiler. Preserve the original source commit, injection
recipes, failed histories, binaries and bytecode snapshots.

If the normal rebuild differs, inspect the difference and make component
provenance explicit before integration. Do not silently adopt an unmeasured VM,
weaken identity checks, or substitute the parked budget-register VM. Full
libtest, unwinding, threads and broad FFI remain separate compatibility work.

The next runtime investigation is static argument-slot information at native
Calls/Returns. Existing qualified profiles place about 40% of token self samples
in those transition entries. Their current assembler starts with empty address
facts, so ordinary-region proofs do not reach the argument-copy path. Measure
dynamic call sites, proven local argument/result slots, unknown cases and the
remaining transition components before selecting an implementation. A proof
must cover VM re-entry and arbitrary register-state contracts, not just the
common native path. Keep guest randomness, faults, budgets, copies, initialization
and source assertions. Sample fractions are not predicted latency savings.
