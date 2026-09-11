# Existing rg-aot test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original line-iteration boundary cases preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median edited command seconds |
|---|---:|
| native | 0.480 |
| interpreter | 0.171 |
| jit | 0.171 |

One successful cold build per mode, with separate empty Cargo artifact directories. Engine bootstrap, the preinstalled toolchain/sysroot, and OS file-cache coldness are excluded.

| Mode | Cold command seconds |
|---|---:|
| native | 3.653 |
| interpreter | 2.728 |
| jit | 2.730 |
