# fre ordinary-test execution survey

198 of 389 discovered test bodies pass in fresh native and custom-JIT processes
at the pinned original revision. Another 191 remain blocked during lowering.
All seven ignored tests are among those blocked entries; none were executed.
No compared test produced a semantic mismatch.

| Instruction ceiling per body | Newly passing bodies |
|---|---:|
| 100 million | 189 |
| 10 billion, retrying only the nine limited cases | 8 |
| 100 billion, retrying only the remaining case | 1 |

The last case executed 17,037,014,946 virtual instructions: 11.084 s in the
custom JIT versus 0.541 s natively. Its synthetic input is about 6.8 MB. This
is a substantial runtime gap, not an end-to-end edit/build speedup measurement.
The survey is partial suite coverage, not support for the whole project.

The same immutable tool, bytecode digests, and freshly built native executable
were checked across all phases. Original test bodies and source pins were
preserved. Native failures, instruction limits, and lowering failures remain
distinct in the raw evidence. Default engine limits were not changed.

[Initial survey](../audit-execution-fre-01/summary.md),
[nine-case retry](../audit-execution-fre-limit-retry-01/summary.json),
[last-case retry](../audit-execution-fre-large-input-retry-01/summary.json),
[combined provenance](summary.json).
