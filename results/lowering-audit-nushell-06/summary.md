# Test-body lowering audit: nushell / nu-protocol

87 of 279 selected bodies lowered; 192 were blocked. The native binary listed 279 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

| First lowering blocker | Bodies |
|---|---:|
| unsupported rvalue &/*tls*/ std::hash::RandomState::new::KEYS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 109 |
| unsupported intrinsic carrying_mul_add | 37 |
| unsize pointer | 10 |
| unsupported cast PointerCoercion(ClosureFnPointer(Unsafe), Implicit) | 10 |
| unsupported intrinsic ptr_mask | 8 |
| MIR unavailable for libc::unix::isatty | 4 |
| MIR unavailable for libc::unix::pthread_mutex_lock | 4 |
| unsupported constant allocation: TypeId { ty: errors::shell_error::bridge::ShellErrorBridge } | 4 |
| unsupported rvalue &/*tls*/ kitest::capture::TEST_OUTPUT_CAPTURE::{constant#0}::{closure#0}::__RUST_STD_INTERNAL_VAL | 2 |
| MIR unavailable for libc::unix::close | 2 |
| expected integer or thin pointer, got *const alloc::sync::ArcInner<str> | 1 |
| unsupported intrinsic catch_unwind | 1 |
