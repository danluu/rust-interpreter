# Checking policy experiment

Dependencies are prepared before timing. These are direct rustc invocations for the selected crate, not complete Cargo loops. Both demand modes perform partial validation of the selected static call graph. Demand-cache commits rustc semantic caches; demand leaves the session unfinished. Five distinct body edits per mode.

| Case | Strict compiler s | Demand compiler s | Demand with committed cache s |
|---|---:|---:|---:|
| rg-aot | 0.043 | 0.036 | 0.033 |
| pgrust-hash | 0.023 | 0.017 | 0.017 |
| pgrust-numeric | 0.215 | 0.059 | 0.059 |
| fre | 0.688 | 0.491 | 0.406 |
| ruff | 1.707 | 1.427 | 1.231 |
| nushell | 0.108 | 0.102 | 0.082 |
