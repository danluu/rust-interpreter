# Existing nushell test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original five parser-keyword assertions preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median command seconds |
|---|---:|
| native | 0.633 |
| interpreter | 0.368 |
| jit | 0.356 |
