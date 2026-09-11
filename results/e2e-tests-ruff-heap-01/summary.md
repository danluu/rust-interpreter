# Existing ruff test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original documentation check for every registered rule preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median edited command seconds |
|---|---:|
| native | 3.831 |
| interpreter | 2.526 |
| jit | 2.695 |

One successful cold build per mode, with separate empty Cargo artifact directories. Engine bootstrap, the preinstalled toolchain/sysroot, and OS file-cache coldness are excluded.

| Mode | Cold command seconds |
|---|---:|
| native | 57.633 |
| interpreter | 25.266 |
| jit | 25.508 |
