# Production edits and existing fre tests

The original exhaustive token-phrase byte-semantics test plus directed restart and route-boundary tests. The custom VM uses an explicit150000 live-allocation budget; native Cargo has its normal allocator. Five production-body refactors leave every original test unchanged..

The JIT explicitly allows150000 live guest allocations; its64MiB guest-byte budget is unchanged. The retained parent at its100000 default fails the exhaustive test, so it is not treated as a successful timing baseline. Native Cargo uses its normal allocator.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

Host build scripts, procedural macros, and their build dependencies use optimization level 0 in every mode. Their first compilation is included in cold command times.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 2.037 | 7.722 |
| jit | 7.315 | 12.294 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
