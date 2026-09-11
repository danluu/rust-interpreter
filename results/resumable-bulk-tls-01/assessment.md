# TLS and destructor qualification

Experimental `78e60cdd`, source `001065a`, passes all 245 commands with the
resumable/persistent JIT options. The recorded matrix contains 85 interpreter
and 85 JIT invocations across 24 exported configurations, three MIR settings
and both leaf-inlining settings. The remaining commands build/run native
controls, export programs and check rejected options.

Original destructor order, state reset between tests, normal callbacks and
strict rejection controls pass. Actual guest panics remain terminal traps;
the native caught-panic result is not synthesized. Successful JIT runs made
5,426 native Calls and 9,413 native Returns. This is not full unwinding support.

[Exact commands, artifacts and frozen inputs](summary.json). Reproduce with
`scripts/validate_tls_destructors.py --run-id NEW_ID --tool-key FULL_KEY
--jit-resumable-calls --jit-persistent-registers` through the supervisor.
The tool uses the benchmark lock. This is compatibility validation, not an
edit-to-test speed measurement or default-retention decision.
