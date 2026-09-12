# Broad native differential validation passes

The exact candidate VM `effc588d` passes all **47,004 commands** of the existing
validator: 23,502 each with default and explicit leaf inlining. The staged
driver preserves the original assertions and verifies the invoked binary
hashes, runtime options and command classifications. JIT execution uses
resumable calls and persistent registers; the custom interpreter and native
Rust outputs remain the references.

Both owned children completed successfully. Full command archives, source
hashes and binary provenance are linked from the summary. This is correctness
qualification, not performance evidence. TLS, complete fre replay and the
repeated command regression gates remain before runtime promotion.
