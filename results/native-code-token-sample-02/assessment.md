# Generated-code attribution

Three fresh token executions of diagnostic `059d818` / `7ad1ccdb` passed the
original assertions. Published bytes and entry ranges come from the same PID
as each recorded live arena and sample. All generated self PCs reconcile with
the dumped code. The original 2f31c6a0 E2E result remains the measured candidate.

Captured 6,931 thread samples; 4,399 are generated self samples.
These perturbed windows are not performance or retention measurements.

| Identified generated instruction class | Share of all thread samples |
| --- | ---: |
| other generated | 32.5% |
| direct register array store | 14.0% |
| native zero range | 11.7% |
| cursor load store | 3.5% |
| direct register array load | 1.6% |
| native abi byte copy | 0.3% |

Entry-kind counts: call stub 622, native tree 2,135, ordinary region 1,642.

Whole native-tree ranges include their call setup and exits. Ordinary and stub
ranges include wrappers and failure tails. Only complete known zero/copy sequences
and direct x0 register-array / x19 cursor loads/stores are identified. Other
instructions stay grouped; computed register addresses are not guessed. Sampling
skid, limited windows and original RNG preclude a causal cost or savings estimate.

The next experiment adds liveness and persistent full-width register assignments
across native edges. Frame lifetime/reuse work stays separate: existing evidence
does not justify repeating argument-only zeroing or unused-local removal.

[Exact attribution](generated-attribution.json) · [Full sample records](summary.json) ·
[Next implementation](../../benchmarks/experiments/bounded-native-calls/VALUE-LIFETIMES-NEXT.md)
