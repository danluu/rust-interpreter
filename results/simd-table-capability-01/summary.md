# Byte table lookup: actual fre coverage

The custom engine now lowers `llvm.aarch64.neon.tbl1.v16i8` into existing scalar
bytecode. This adds 29 passing fre tests. The audit grows from 198 to 227 lowered
ordinary bodies out of 389; another 162 remain blocked. The VM binary and bytecode
version are unchanged. No external interpreter or native guest fallback is used.

The implementation snapshots both operands, selects a safe table index before
loading, and returns zero for unsigned indices outside 0–15. It is checked against
native hardware and independent array semantics for all 256 indices in every
lane, signed data, aliases, repeated calls, and three MIR configurations.
[Rust intrinsic documentation](https://doc.rust-lang.org/core/arch/aarch64/fn.vqtbl1q_u8.html).

71 focused SIMD commands, 79 audit-artifact commands, 99 launcher checks, and
23,502 native differential/rejection commands pass. The real audit then retained
227 programs. All 29 new bodies and 41 old bodies with changed bytecode passed
fresh native/JIT comparisons; the other 157 retain the exact previously tested
bytecode and VM hashes. This reuse is explicit, not a claim that all 227 were
rerun in the new survey.

67 of the 70 compared bodies passed at 100 million instructions. The other three
passed when retried at 10 billion. Two new exhaustive cases took 6.668 and 6.425 s
in the JIT versus 0.339 and 0.258 s natively. This is compatibility evidence and
runtime diagnosis; production-edit timing is measured separately.

Of the 97 original table-intrinsic blockers, 29 now pass; most others expose
OS/threading or TLS-destructor dependencies. Six expose a missing integer ordered
SIMD reduction. First-blocker counts do not predict passing-test counts.

[Validation](../simd-table-validation-01.json),
[new audit](../lowering-audit-fre-simd-table-01/summary.md),
[execution survey](../audit-execution-fre-simd-table-01/summary.md),
[retry](../audit-execution-fre-simd-table-limit-retry-01/summary.json),
[provenance and per-test evidence](summary.json).

The six-test packed-literal workflow passes five production refactors and a wrong
byte-class edit in all engines: native **1.508 s**, interpreter **0.971 s**, JIT
**0.951 s** median whole-command times. Its seventh regex-reference test remains
blocked and is explicitly excluded.
[Production-edit measurements](../e2e-workflow-fre-packed-literal-set-02/summary.md).
