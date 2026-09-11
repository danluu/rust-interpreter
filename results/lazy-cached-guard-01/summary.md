# Cached native compilation checks

The custom VM now keeps the already-compiled check inline and moves first
compilation into a cold helper. All130 bytecode tests, two23,502-command native
differential suites,245 TLS checks, and the targeted compiler/runtime gates pass.
The retained-program replay preserves381 guest passes, one known allocation-count
limit, and seven ignored tests. All382 fresh native controls pass.

| Production-edit workflow | Prior JIT median | Candidate median | Native median | Paired command change | Paired execution change | Command wins vs prior / native |
|---|---:|---:|---:|---:|---:|---:|
| [TLS, MIR3 with larger inlining](../paired-lazy-cached-guard-forward-anchored-tls-01/summary.md) | 1.338s | 1.350s | 1.738s | +15.302ms | −2.461ms | 2/5 / 5/5 |
| [Folded trie, ordinary MIR3](../paired-lazy-cached-guard-folded-literal-trie-01/summary.md) | 4.631s | 4.598s | 3.859s | −188.234ms | −95.734ms | 3/5 / 0/5 |

Execution improves in allten pairs. Complete commands improve in onlyfive: Cargo
adds19ms in the TLS paired median and saves47ms in folded trie. Allfourteen artifact
pairs are byte-identical, every wrong production edit is rejected, and the original
tests are unchanged. Allseven baseline states per workflow also match the prior
candidate's retained artifacts. These are full source-edit/build/test measurements.
The medians from separate cohorts are not added to previous experiments' savings.

The runtime-only screen improves allsix TLS and allsix folded-trie pairs, but the
small formerly code-limited case improves onlytwo ofsix. Its+130ms outlier is retained.
All measured VM statistics except compilation time match within the runtime pairs.
Inspection of the old VM found two helper calls and a240-byte stack frame before
returning from a cached check; those helper symbols are absent in the new binary.

Retain this as an experimental runtime improvement. Complete-command results are
mixed, and there is no broad build-time speed claim. The16MiB code cap, strict Rust
frontend and full bytecode validation, own-interpreter decline behavior, and existing
allocation limits remain. Whole applications, guest threads, arbitrary OS/FFI calls,
and actual unwinding remain outside the supported scope.

A separate same-engine comparison of ordinary MIR3 and larger MIR inlining on
folded trie is complete: allfive edited commands improve by a paired median428ms,
including369ms in execution. Median commands are3.077s tuned JIT,3.429s ordinaryMIR3,
and1.883s native. The candidate still loses allfive comparisons with native.
Allseven baseline artifacts match the preceding ordinaryMIR3 run; no savings are
summed across these separate runs. [MIR follow-up](../paired-folded-mir-inline8-01/summary.md).
