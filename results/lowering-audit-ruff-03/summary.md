# Test-body lowering audit: ruff / ruff_linter

70 of 2832 selected bodies lowered; 2762 were blocked. The native binary listed 2832 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

| First lowering blocker | Bodies |
|---|---:|
| unsupported rvalue &/*tls*/ insta::settings::CURRENT_SETTINGS::{constant#0}::{closure#0}::__RUST_STD_INTERNAL_VAL | 1080 |
| unsupported rvalue &/*tls*/ test::MAX_ITERATIONS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 913 |
| unsupported intrinsic caller_location | 257 |
| unsupported cast PointerCoercion(ClosureFnPointer(Unsafe), Implicit) | 167 |
| MIR unavailable for libc::unix::pthread_mutex_lock | 132 |
| MIR unavailable for std::backtrace_rs::backtrace::libunwind::uw::_Unwind_Backtrace | 98 |
| unsupported intrinsic ptr_mask | 47 |
| MIR unavailable for libc::unix::fstat | 25 |
| MIR unavailable for psm::rust_psm_stack_pointer | 24 |
| unsupported dynamic layout for std::path::Path | 8 |
| unsupported rvalue &/*tls*/ insta::runtime::RECORDED_DUPLICATES::{constant#0}::{closure#0}::__RUST_STD_INTERNAL_VAL | 5 |
| MIR unavailable for libc::unix::stat | 3 |
| unsupported rvalue &/*tls*/ std::hash::RandomState::new::KEYS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 2 |
| MIR unavailable for libc::unix::confstr | 1 |
