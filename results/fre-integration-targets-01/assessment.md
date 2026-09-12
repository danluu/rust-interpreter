# First real integration run: entry-name construction error

All ten native integration targets passed their 52 assertions. The custom
commands stopped during entry selection, before executing any guest code.
The experiment driver incorrectly prepended the Cargo crate name to native
libtest names; rustc reports local definition paths without that prefix.

This is a driver error, not evidence that these tests require unsupported VM
operations. Keep all original logs. Correct the selection to use the exact
native test names and reuse the already checked dependency cache for the next
coverage attempt. The source pin, compiler/runtime, original assertions and
explicit compilation settings stay the same. No performance result is claimed.
