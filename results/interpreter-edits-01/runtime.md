# Custom interpreter execution scaling

Five alternating samples per condition, using previously built matching revisions; executable startup has been warmed. Each iteration calls the selected production routine. These are routine throughput probes, not full application workloads.

| Routine | Calls | Native s | Interpreter s |
|---|---:|---:|---:|
| pgrust-hash | 0 | 0.0017 | 0.0018 |
| pgrust-hash | 1024 | 0.0017 | 0.0028 |
| pgrust-hash | 16384 | 0.0017 | 0.0172 |
| pgrust-hash | 131072 | 0.0021 | 0.1249 |
| pgrust-numeric | 0 | 0.0017 | 0.0018 |
| pgrust-numeric | 1024 | 0.0017 | 0.0025 |
| pgrust-numeric | 16384 | 0.0017 | 0.0150 |
| pgrust-numeric | 131072 | 0.0021 | 0.1068 |
| fre | 0 | 0.0018 | 0.0017 |
| fre | 1024 | 0.0017 | 0.0027 |
| fre | 16384 | 0.0018 | 0.0149 |
| fre | 131072 | 0.0024 | 0.1080 |
| ruff | 0 | 0.0018 | 0.0017 |
| ruff | 1024 | 0.0017 | 0.0025 |
| ruff | 16384 | 0.0018 | 0.0140 |
| ruff | 131072 | 0.0020 | 0.0988 |
| nushell | 0 | 0.0026 | 0.0018 |
| nushell | 1024 | 0.0026 | 0.0022 |
| nushell | 16384 | 0.0026 | 0.0090 |
| nushell | 131072 | 0.0030 | 0.0595 |
| rg-aot | 0 | 0.0022 | 0.0022 |
| rg-aot | 1024 | 0.0021 | 0.0033 |
| rg-aot | 16384 | 0.0023 | 0.0183 |
| rg-aot | 131072 | 0.0029 | 0.1276 |
