# Existing ruff test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original documentation check for every registered rule preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median command seconds |
|---|---:|
| native | 3.731 |
| interpreter | 2.506 |
| jit | 2.502 |
