# Test-body lowering audit: nushell / nu-protocol

47 of 279 selected bodies lowered; 232 were blocked. The native binary listed 279 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

| First lowering blocker | Bodies |
|---|---:|
| unsupported dynamic layout for alloc::sync::ArcInner<dyn std::error::Error + std::marker::Send + std::marker::Sync> | 88 |
| only immutable, non-thread-local Rust statics are supported | 70 |
| unsupported rvalue &/*tls*/ std::hash::RandomState::new::KEYS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 39 |
| unsupported cast PointerCoercion(ClosureFnPointer(Unsafe), Implicit) | 10 |
| unsize pointer | 9 |
| unsupported intrinsic caller_location | 5 |
| unsupported constant allocation: TypeId { ty: errors::shell_error::bridge::ShellErrorBridge } | 3 |
| CLI entry result must be an integer, bool, char, or unit | 2 |
| unsupported intrinsic ptr_mask | 2 |
| MIR unavailable for libc::unix::close | 2 |
| expected integer or thin pointer, got *const alloc::sync::ArcInner<str> | 1 |
| unsupported intrinsic catch_unwind | 1 |
