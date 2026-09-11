# Existing fre test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original seven codec boundary roundtrips preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median command seconds |
|---|---:|
| native | 1.237 |
| interpreter | 0.688 |
| jit | 0.681 |
