# Test-body lowering audit: fre / fre-kernels

231 of 389 selected bodies lowered; 158 were blocked. The native binary listed 389 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

The experimental bounded bytecode leaf inliner ran on each lowered body. Execution evidence for default bytecode does not establish that these transformed artifacts pass.

Retained 231 independently validated programs (227,565,132 serialized bytes). Each file has a writer-recorded SHA-256 checked by the launcher; the manifest belongs to Cargo's exact selected metadata sidecar. These programs have not been executed. Test-harness metadata still needs inspection before a broad execution survey.

Compiler test metadata identifies 231 lowered ordinary tests, 7 ignored tests, and 0 expected-panic tests. Lowering and harness classifications are separate; none is counted as executed.

| First lowering blocker | Bodies |
|---|---:|
| MIR unavailable for libc::unix::pthread_mutex_trylock | 62 |
| MIR unavailable for std::sys::sync::thread_parking::darwin::dispatch_semaphore_signal | 61 |
| thread-local destructor registration is not yet supported | 28 |
| MIR unavailable for libc::unix::bsd::apple::clock_gettime | 6 |
| MIR unavailable for libc::unix::fstat | 1 |
