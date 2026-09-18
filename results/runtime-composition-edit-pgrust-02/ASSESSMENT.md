# Pgrust hashfn held-out history

The154-command history passes its unchanged regression guard. Candidate/adopted
wall ratio is1.00313849 and child CPU ratio is1.00271664. Both differences are
inside A/A variation (wall1.826877%, CPU1.440571%). The required wall/CPU margins,
1.02140726 and1.01712235, pass1.05. This establishes no incremental speedup.

Candidate/ordinary-native wall ratio is **1.04813587** on the current host.
The custom command is about4.8% slower in this comparison. Do not substitute the
more favorable historical native ratio from the earlier adopted-runtime campaign;
these measurements use their own matched native controls.

All four original tests, expected wrong-edit failures, paired bytecode/catalog
identities and source restoration pass. Only15 genuinely edited pairs enter
latency ratios. Normal entropy, two Cargo/prepared workers, native libtest default
concurrency, strict checking and original assertions remain unchanged.

The outer controller again timed out waiting for the shared lock after the
successful case. A separate audit-only recovery must close checkpoint3 from its
462 retained commands without repeating measurements. The prior recovered
checkpoint2 remains immutable. Private rg-aot, Nushell and both full-parser guards
remain pending, and main still uses the adopted scratch/scalar runtime.

[Summary](summary.json), [closure](closure.json), [terminal](terminal.json).
