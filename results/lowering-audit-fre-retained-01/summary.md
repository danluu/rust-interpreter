# Test-body lowering audit: fre / fre-kernels

198 of 389 selected bodies lowered; 191 were blocked. The native binary listed 389 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

Retained 198 independently validated programs (112,499,805 serialized bytes). Each file has a writer-recorded SHA-256 checked by the launcher; the manifest belongs to Cargo's exact selected metadata sidecar. These programs have not been executed. Test-harness metadata still needs inspection before a broad execution survey.

Compiler test metadata identifies 198 lowered ordinary tests, 7 ignored tests, and 0 expected-panic tests. Lowering and harness classifications are separate; none is counted as executed.

| First lowering blocker | Bodies |
|---|---:|
| unsupported target intrinsic llvm.aarch64.neon.tbl1.v16i8 | 97 |
| MIR unavailable for libc::unix::pthread_mutex_trylock | 61 |
| MIR unavailable for std::sys::sync::thread_parking::darwin::dispatch_semaphore_signal | 21 |
| MIR unavailable for libc::unix::bsd::apple::clock_gettime | 6 |
| thread-local destructor registration is not yet supported | 5 |
| MIR unavailable for libc::unix::fstat | 1 |
