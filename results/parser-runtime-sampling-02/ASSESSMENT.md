One original parser test passed on the adopted runtime. All 85 generated self
samples map to the same process's verified machine-code/operation map: 32 Call,
15 Copy, 9 budget, 7 Load, with smaller categories retained in the report.
The 253 captured thread samples also include 113 post-execution diagnostic,
15 JIT preparation, 8 frame reservation and 2 heap samples. Do not use their
shares as a speedup forecast: this is a short, perturbed partial window.

The eight frame-reservation samples are in bzero. Six host samples are in the
interpreter's case-list find, suggesting an independently simpler large-switch
lookup experiment. Check the saved case dimensions and interpreted frequency
first; no frame-elision or bounds change is warranted from byte weights alone.
The generic host classifier does not recognize execute_prepared_impl as
dispatcher_self, so those samples remain visible in other_host_self, not lost.

All original assertions, exact selected-entry receipt, fallback count one and
same-process map checks pass. Nine attribution controls are retained through
unchanged direct source bindings. The closure verifies 257 inputs and 29 evidence
files. Attempt 01 failed preflight with zero guest commands and is preserved.
