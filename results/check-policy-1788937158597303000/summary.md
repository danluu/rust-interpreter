# Checking policy experiment

Dependencies are prepared before timing. These are direct rustc invocations for the selected crate, not complete Cargo loops. Demand mode performs partial validation and currently does not preserve the normal incremental-query cache across invocations. Five distinct body edits per mode.

| Case | Strict compiler s | Demand compiler s |
|---|---:|---:|
| rg-aot | 0.043 | 0.037 |
| pgrust-hash | 0.023 | 0.017 |
| pgrust-numeric | 0.223 | 0.061 |
| fre | 0.693 | 0.502 |
| ruff | 1.729 | 1.453 |
| nushell | 0.114 | 0.109 |
