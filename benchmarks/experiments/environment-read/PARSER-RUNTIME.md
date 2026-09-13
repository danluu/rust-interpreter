# Full parser runtime diagnosis

The completed matched-incremental comparison runs all original 114 parser tests
and is 23.03% slower than native on paired changed-source wall time. Saved suite
receipts identify `tests_dump::c_reference_vectors` as the longest test. Both
prepared workers already report one compilation decline on their first test,
with only about 2.7 MiB of published code. Determine the function and actual
admission/emission cause before changing capacity or code generation.

One fresh diagnostic invocation uses the exact final-restored custom-A artifact
and catalog from `pgrust-parser-edits-incremental-history-01`, immutable qualified
VM, resumable calls, persistent registers and unchanged instruction/allocation
limits. Select the original C reference-vector test through its bound catalog.
Capture existing logical profiling, published code and verified operation maps.
No source change, compiler invocation, external guest backend or timing claim.
The cold JIT publication order differs from the prepared-suite worker history;
identify any coverage difference explicitly. Counts are not latency or retired
host instructions. Do not infer failure reasons solely from missing code.

Acquire the shared lock for at most 45 seconds, require 8 GiB free, record exact
process identities, and retain all failures. Output bounds are the existing
256 MiB profile/map limits and 16 MiB code limit. No unrelated process control.
