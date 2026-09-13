The current compiler/measured-runtime integration passes its complete audit:
513 workspace Rust tests per profile, two explicit remapping tests with 130
internal commands, 119 strict/cache/Cargo controls, 40 real-project histories
and all 114 original pgrust parser tests. All five histories reproduce their
recorded bytecode and catalogs exactly. Frozen source, tool, artifact and
terminal records verify; Git source bindings preserve the completed evidence
before later main integration changes.

Adopt the guarded-local-facts/scalar-Copy composition. Its separate 726-command
campaign passed all five gates, with primary paired wall/CPU ratios of
0.95266/0.96175 against the prior custom runtime. That is a 4.73%/3.83% reduction;
folded, pgrust, private and Nushell comparisons pass the regression guards.
Nushell's incremental change stays inside measured variation. The primary
custom/native wall ratio remains 1.641; this is not a claim of native parity.

The measured VM is unchanged in the newly qualified compiler composition.
Complete-command timing ratios remain bound to the original measured exporter,
wrapper and two-worker settings. These integration controls establish current
compiler compatibility without repeating timing histories. The 16 MiB default
and the parser's known large-function decline remain unchanged. Continue with
actual-emitter evidence for local-value losses before another runtime screen.
