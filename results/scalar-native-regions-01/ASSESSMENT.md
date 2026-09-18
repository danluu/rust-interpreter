# Continue with bounded value reuse

All 16 focused controls pass. Eight commands reconstruct both adopted schema-2
captures exactly, including scalar bodies, without executing guests or publishing
code. The closure binds 286 source/input files and 29 retained artifacts.

| Partial self-PC samples | Block | Exhaustive |
| --- | ---: | ---: |
| Generated code | 1,561 | 1,231 |
| Small memory operations | 605 | 281 |
| Remaining payload loads with all bytes available earlier in this segment | 109 | 51 |
| Payload stores fully overwritten before a segment boundary | 7 | 2 |

This supports investigating captured value reuse inside ordinary native regions.
Store elimination alone has little sampled coverage. Opportunities are distributed
across functions and widths, rather than one leaf or one hot store site. Existing
load forwarding is excluded by attributing only remaining payload instructions.

Availability assumes retaining the captured values. This census neither assigns
registers nor models capture, extraction, publication or compilation costs. It is
not a native lowering proof, retired-instruction count, or latency estimate. Both
windows are partial and perturbed. No runtime adoption or timing follows yet.

The next step is a bounded value-origin and lifetime model, retaining conservative
unknown-alias and fault barriers. Compare implementation cost with actual emitted
load coverage before a prototype. Keep strict frontend checking, original tests,
the fixed changed-source primary and all larger-project/parser guards.

Source: `e95f04be`. Raw typed accesses, exact maps, records and sample attribution
remain linked from [summary.json](summary.json) and [closure.json](closure.json).
