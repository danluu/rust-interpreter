# Test-body lowering audit: nushell / nu-protocol

162 of 279 selected bodies lowered; 117 were blocked. The native binary listed 279 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

| First lowering blocker | Bodies |
|---|---:|
| MIR unavailable for std::sys::sync::thread_parking::darwin::dispatch_semaphore_signal | 40 |
| MIR unavailable for libc::unix::bsd::apple::clock_gettime | 21 |
| MIR unavailable for libc::unix::pthread_mutex_lock | 16 |
| MIR unavailable for libc::unix::pthread_mutex_unlock | 10 |
| MIR unavailable for libc::unix::getcwd | 10 |
| unsupported constant allocation: TypeId { ty: errors::shell_error::bridge::ShellErrorBridge } | 7 |
| MIR unavailable for libc::unix::stat | 5 |
| MIR unavailable for libc::unix::isatty | 4 |
| MIR unavailable for libc::unix::mkdir | 1 |
| expected integer or thin pointer, got *const alloc::sync::ArcInner<str> | 1 |
| unsupported intrinsic catch_unwind | 1 |
| thread-local destructor registration is not yet supported | 1 |
