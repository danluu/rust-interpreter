# Test-body lowering audit: ruff / ruff_linter

70 of 2832 selected bodies lowered; 2762 were blocked. The native binary listed 2832 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

| First lowering blocker | Bodies |
|---|---:|
| CLI entry result must be an integer, bool, char, or unit | 2224 |
| only immutable, non-thread-local Rust statics are supported | 517 |
| unsupported cast PointerCoercion(ClosureFnPointer(Unsafe), Implicit) | 9 |
| unsupported dynamic layout for std::path::Path | 8 |
| MIR unavailable for libc::unix::stat | 3 |
| unsupported intrinsic caller_location | 1 |
