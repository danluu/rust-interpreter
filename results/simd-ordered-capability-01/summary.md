# Integer ordered SIMD reductions

The custom lowering now implements ordered integer vector sums and products,
including the initial scalar accumulator and wrapping at the element width.
It uses existing scalar bytecode; the qualified VM binary is unchanged.
[Sum contract](https://doc.rust-lang.org/nightly/core/intrinsics/simd/fn.simd_reduce_add_ordered.html),
[product contract](https://doc.rust-lang.org/nightly/core/intrinsics/simd/fn.simd_reduce_mul_ordered.html).

Four additional original fre tests pass against native Rust. The audit now lowers
231 of 389 bodies; 158 remain blocked by synchronization, TLS destructors, clocks,
or file metadata. Two of the six reduction-blocked bodies now reach unsupported
synchronization calls. Seven ignored tests remain among the blocked entries and
were not executed.

All four new programs and 54 old programs with changed bytecode were compared
again in fresh native/JIT processes: 57 passed at 100 million instructions and
one previously known longer case passed when retried at 10 billion. The other
173 retain identical previously passing bytecode and VM hashes. This explicit
reuse supports 231 ordinary-test results; it is not a claim of 231 fresh runs.

71 focused SIMD commands cover signed and unsigned wrapping, nonidentity initial
accumulators, lanes through 128 bits, native vaddv wrappers, table lookup, aliases,
and three MIR configurations. All 79 audit-artifact checks, 99 launcher checks,
and 23,502 native differential/rejection commands pass. Floating vector reductions
remain unsupported. All eleven production workflows now pass on the same frozen build, including
wrong-edit rejection and an isolated SHA-1 timing rerun.
[Corpus results](../e2e-simd-coverage-corpus-01/summary.md).

[Validation](../simd-ordered-validation-01.json),
[audit](../lowering-audit-fre-simd-ordered-01/summary.md),
[execution survey](../audit-execution-fre-simd-ordered-01/summary.md),
[retry](../audit-execution-fre-simd-ordered-limit-retry-01/summary.json),
[per-test evidence](summary.json).
