# Existing pgrust test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original 100,000-iteration roundtrip loop preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median edited command seconds |
|---|---:|
| native | 0.662 |
| interpreter | 0.873 |
| jit | 0.620 |
