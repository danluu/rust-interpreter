# Actual register-file traffic does not justify a larger register bank

Eight controls pass, including an independent 14-word host assembler oracle.
Both closed adopted captures reconcile every generated sample: 1,561 block and
1,231 exhaustive, with zero ambiguous category assignments. Closure verifies
86 frozen inputs and the exact object, logs, source, maps and sampled words.
No guest program runs and no production instruction changes.

| Captured self PCs | Block | Exhaustive |
| --- | ---: | ---: |
| Register-file loads, low / high | 74 / 8 | 73 / 6 |
| Register-file stores, low / high | 10 / 118 | 13 / 75 |
| Large register address materialization | 1 | 0 |
| All register-file accesses and address words | 211 (13.52%) | 167 (13.57%) |
| Of those, loads in ordinary operation spans | 20 | 17 |
| Of those, stores in flush spans | 116 | 80 |

The high-store `value` category means a physical payload register rather than
xzr. It does **not** establish a nonzero high value: flush_facts materializes
known zero into x10 too. Adjacent low/high instruction sample imbalance is not
a retired-instruction count or a per-store latency estimate. Static scans cover
2,825,973 / 3,437,394 ordinary words; other memory bases/forms and scalar bodies
remain separate. Recognizing an access does not prove it removable.

Do not repeat width packing, a larger ordinary cache, paired spills, successor-
only flush or cross-region local rematerialization from this result. Their prior
coverage and timing failures remain relevant. In particular, the earlier
consumed-flush census already identified most flush samples as branch operands
that are dead afterward; the successor-only implementation still failed its full
changed-source gate. The whole-function width proof cannot omit an upper store
without a separate initialized-storage proof across reused frames and VM exits.
The old whole-CFG Local census found negligible additional memory-address uses.

Next investigate demand-driven ordinary-region compilation. Current full-function
emission includes unreachable native regions and declines oversized functions;
a bounded saved-profile/code census can size these costs before a design change.
Count actual executed regions, emitted bytes and preparation separately. Cold
code size is not a timing estimate. Keep compiler/exporter ownership separate,
all current benchmark gates and the adopted runtime.
