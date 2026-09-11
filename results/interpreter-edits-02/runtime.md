# Custom interpreter execution scaling

Five alternating samples per condition, using previously built matching revisions; executable startup has been warmed. Each iteration calls the selected production routine. These are routine throughput probes, not full application workloads.

| Routine | Calls | Native s | Interpreter s |
|---|---:|---:|---:|
| pgrust-hash | 0 | 0.0018 | 0.0018 |
| pgrust-hash | 1024 | 0.0017 | 0.0028 |
| pgrust-hash | 16384 | 0.0020 | 0.0175 |
| pgrust-hash | 131072 | 0.0022 | 0.1255 |
| pgrust-numeric | 0 | 0.0017 | 0.0019 |
| pgrust-numeric | 1024 | 0.0017 | 0.0026 |
| pgrust-numeric | 16384 | 0.0017 | 0.0145 |
| pgrust-numeric | 131072 | 0.0020 | 0.1070 |
| fre | 0 | 0.0017 | 0.0018 |
| fre | 1024 | 0.0017 | 0.0026 |
| fre | 16384 | 0.0018 | 0.0152 |
| fre | 131072 | 0.0024 | 0.1086 |
| ruff | 0 | 0.0019 | 0.0017 |
| ruff | 1024 | 0.0018 | 0.0026 |
| ruff | 16384 | 0.0018 | 0.0141 |
| ruff | 131072 | 0.0019 | 0.1005 |
| nushell | 0 | 0.0027 | 0.0018 |
| nushell | 1024 | 0.0025 | 0.0023 |
| nushell | 16384 | 0.0026 | 0.0091 |
| nushell | 131072 | 0.0030 | 0.0618 |
| rg-aot | 0 | 0.0018 | 0.0018 |
| rg-aot | 1024 | 0.0018 | 0.0030 |
| rg-aot | 16384 | 0.0019 | 0.0173 |
| rg-aot | 131072 | 0.0027 | 0.1259 |
