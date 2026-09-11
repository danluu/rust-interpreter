# Explicit live-allocation budget

The retained implementation makes the remaining ordinary fre test executable with an explicit 150,000-live-allocation limit. It adds `Limits::allocations` and `--allocation-limit` to the VM and project launcher. The default stays 100,000, requests above one million are rejected, and the guest-byte budget is separate. Zero disables guest allocation. Realloc continues to count its temporary replacement before releasing the original; an unsuccessful replacement preserves the original allocation.

The default 100,000 limit fails identically in the retained VM and candidate. The uninstrumented candidate passes the entire original exhaustive test at both 150,000 and 250,000 with zero declined native functions. The JIT emitter and MIR lowering source are unchanged; both tool binaries were freshly built. All 161 bytecode tests pass. The final source adds three persistent C-boundary tests to the measured source; fresh builds reproduce both measured binaries exactly.

The diagnostic peaks at 117,707 live allocations, 7,498,072 heap bytes and 8,168,856 total guest bytes, and releases all allocations by the end. It records 1,021,448 allocations/deallocations and 470,880 reallocations. Free-range scans reach at most 30 entries. Process RSS is about 178 MB and includes bytecode, JIT and other host data; it is not allocator metadata alone. Instrumented timings are excluded from qualification.

Five production-body refactors run the unchanged exhaustive token-phrase test plus directed restart and route-threshold tests. Native and JIT both reject the deliberately wrong production edit and pass all valid edits. Native uses its normal allocator; the custom VM explicitly allows 150,000 live allocations.

| New token-phrase workflow | Native Cargo | Custom JIT |
|---|---:|---:|
| Median edited command | 2.037 s | 7.315 s |
| Cold command | 7.722 s | 12.294 s |

The JIT loses all five complete edited commands. Its median execution stage is 5.884 seconds and Cargo stage 1.333 seconds. The old default failure is not treated as a successful timing baseline. This is a capability gain, with a substantial runtime gap to native. [Full edit results](../e2e-allocation-budget-token-phrase-01/summary.md).

Default-limit comparisons against retained build 87abb:

| Workflow | Paired command change | Execution change | Wins |
|---|---:|---:|---:|
| [folded-literal-trie](../paired-allocation-budget-folded-literal-trie-01/summary.md) | -30.7 ms | -3.2 ms | 4/5 |
| [pgrust-interpreter](../paired-allocation-budget-pgrust-interpreter-01/summary.md) | +9.8 ms | +10.1 ms | 2/5 |

All recorded default-comparison artifacts match the retained artifact for each source state. Assertions, wrong-edit rejection and source restoration are checked. Five pairs per workflow and independent stage medians limit conclusions.

The six-pair same-artifact runtime screen retains folded-trie +11.3 ms, TLS +1.0 ms, SHA-1 −2.0 ms and interpreter-control +12.5 ms. Complete folded profiles match exactly. The interpreter regression remains relevant even if full-command variation masks it.

The first byte-budget fixture omitted the 16-byte null-address prefix; the corrected fixture checks exact admission and allocation boundaries at 175/176/184/192 bytes. A separate C fixture originally expected a read-only error for address zero; its correction checks invalid access at zero and read-only access at eight. Both failures and original fixtures are preserved; production code did not change for these corrections. The benchmark preflight also rejected an ambiguous source replacement before changing any files, then narrowed it to the short-input path.

All 47,004 native differential commands and 245 TLS checks pass. Retained-program replay with the explicit 150,000 limit passes all 382 non-ignored fre bodies against 382 fresh native controls; seven tests remain ignored. All passes have zero declined native functions. This replay reuses exact bytecode and does not re-export every body. Both default-comparison workflows re-export all seven states and verify exact artifact equality. Two alternatives, boxed bounds and reordered limit fields, failed to remove the interpreter regression and are archived without integration. The simple implementation is retained with that cost documented. The original exhaustive-test profile records 195,133,302 native entries, 8,421,565 interpreted byte comparisons and 11,913,117 dynamic copies. These are execution counts, not CPU-time shares; native byte comparison is the next bounded hypothesis. Whole applications, arbitrary OS/FFI calls, guest threads and native unwinding remain unsupported. No broad warm-build gain is established.
