# Historical validation count correction

The older `af9aa691` / byte-identical production `57a54edd` qualification ran
**47,004 commands**, not 47,004 unique tests or native comparisons. Recounting
both preserved command archives gives this exact partition:

| Command category | Each inlining mode | Both modes |
| --- | ---: | ---: |
| Custom interpreter | 11,119 | 22,238 |
| Custom JIT | 11,119 | 22,238 |
| Default-engine corrupt-artifact rejection | 1 | 2 |
| Native program/test execution | 941 | 1,882 |
| Native compiler/build | 118 | 236 |
| MIR exporter | 204 | 408 |
| Total | 23,502 | 47,004 |

Some native invocations produce many oracle values, and many inputs repeat
across lowering configurations. Neither rows nor totals establish a unique-case
count. Each mode includes 92 expected failures in each explicit custom engine,
79 native failure exits and 43 exporter rejections. These remain part of the
suite. The audit verifies the full command counts and hashes, without rerunning
or changing any historical test or performance measurement.

Current status/review text now uses the exact command categories. Historical
reports remain intact. The separate 245-command TLS qualification and 382
passing/7 ignored fre bodies are separate evidence, and neither transfers to
a new runtime without rerunning the relevant qualification.

[Recount and source hashes](summary.json) ·
[Reproducer](../../scripts/audit_validation_counts.py)
