# Test-body lowering audit: fre / fre-kernels

5 of 5 selected bodies lowered; 0 were blocked. The native binary listed 389 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

Guest MIR flags: `-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. The exact collection invocation and RUSTFLAGS are recorded and hashed; native controls retain their ordinary Cargo profile.

The experimental bounded bytecode leaf inliner ran on each lowered body. Execution evidence for default bytecode does not establish that these transformed artifacts pass.

Try callbacks execute on the normal-return path. Actual panic, unwinding and VM faults fail execution; no caught-panic result is synthesized.

Retained 5 independently validated programs (4,069,420 serialized bytes). Each file has a writer-recorded SHA-256 checked by the launcher; the manifest belongs to Cargo's exact selected metadata sidecar. These programs have not been executed. Test-harness metadata still needs inspection before a broad execution survey.

Compiler test metadata identifies 5 lowered ordinary tests, 0 ignored tests, and 0 expected-panic tests. Lowering and harness classifications are separate; none is counted as executed.

| First lowering blocker | Bodies |
|---|---:|
