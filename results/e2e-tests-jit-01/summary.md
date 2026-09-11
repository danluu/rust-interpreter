# Existing pgrust test: edit to result

Full commands, including launcher and Cargo; five test-source edits, unchanged 100,000-iteration workload. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median command seconds |
|---|---:|
| native | 0.665 |
| interpreter | 1.170 |
| jit | 0.948 |
