# Exact failed-emission cost in the checked parser

The large reached parser function declines because ordinary emission exceeds
remaining native code capacity. It is not a branch-encoding or resume-table
failure in this replay. Each worker stages about14.4MB, reaches roughly bytecode
PC104,263–105,206 of140,615 operations, then discards the complete staged result.
The current remaining budget is about3.61–3.62million four-byte words; previously
published code occupies the rest of the unchanged16MiB arena.

For the five valid edits, these unsuccessful ordinary-emission intervals are
about21–23ms per worker. Preparing their scalar callees takes another4.6–5.3ms.
The intervals overlap across two workers and include diagnostic overhead; they
are not additive command savings or acceptance timings. Each current worker has
one reported decline and no truncated records. Numeric IDs shift1357→1361 with
the edited Program, which is why reuse must bind actual current inputs.

The observer1c473ada changes no native words or admission decisions. It is behind
jit-preparation-observer, separate from timing binaries.31 focused controls per
profile pass, including71 actual failed emissions that exercise its64-row bound.
All24 owned sessions and46 fixture clients are reaped. Actual replay0db84ae1
matches16 saved suites/1,824 original invocations, including exact wrong-edit
assertion text. Kernel CPU reconciles at exit. Verification is off in this
attribution replay; the preceding independent candidate replay already checked
every restored native template against fresh emission.

Qualification60896/60932 is closed78117/78120. Replay89264/89267 is closed94661/
94724. Results:results/session-preparation-observer-qualification-01 and
results/session-preparation-observer-parser-01. This resolves the earlier unknown
ordinary decline; it does not endorse increasing capacity. The prior32MiB screen
and conditional-demand parser primary remain failed under their original gates.

Next test an explicit experimental size-based tiering policy using the existing
65,536-operation analysis boundary: keep oversized functions in the interpreter
and JIT smaller functions. This is a compilation-cost heuristic, not proof that
every oversized function would exceed capacity. It must retain current checking,
callee execution, budgets and fresh state. Some large compilable hot functions
could lose native execution, so original project guards must decide adoption.
Compose with the qualified request-cost session and compare against adopted,
A/A, session-without-history and ordinary native under unchanged gates. No new
native cache formats, relaxed checking, larger arenas or unchanged retry.
