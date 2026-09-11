# Test-body lowering audit: fre / fre-kernels

327 of 389 selected bodies lowered; 62 were blocked. The native binary listed 389 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

The experimental bounded bytecode leaf inliner ran on each lowered body. Execution evidence for default bytecode does not establish that these transformed artifacts pass.

Unavailable foreign and catch_unwind intrinsic calls remain explicit terminal traps. A retained body may still stop at one during execution; call-site metadata is recorded per body.

Retained 327 independently validated programs (453,864,289 serialized bytes). Each file has a writer-recorded SHA-256 checked by the launcher; the manifest belongs to Cargo's exact selected metadata sidecar. These programs have not been executed. Test-harness metadata still needs inspection before a broad execution survey.

Compiler test metadata identifies 320 lowered ordinary tests, 7 ignored tests, and 0 expected-panic tests. Lowering and harness classifications are separate; none is counted as executed.

| First lowering blocker | Bodies |
|---|---:|
| function expansion limit reached | 62 |
