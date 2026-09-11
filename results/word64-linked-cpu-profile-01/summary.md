# Qualified word64 engine: CPU sampling

A separate diagnostic run collected 773 samples from the qualified engine. 322 samples were in the generated guest-code mapping; the remaining samples were in the host loop or its callees. Frame reservation/zeroing and memory copies appear prominently. The host interpreter and JIT loops still share an `execute_observed` wrapper.

This one-second profile guides investigation; it is not a speedup measurement. Generated addresses were verified against the executable mapping, and raw stacks and process-ownership checks are retained.

[Raw provenance and limitations](summary.json).
