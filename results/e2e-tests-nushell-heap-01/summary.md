# Existing nushell test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original five parser-keyword assertions preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median edited command seconds |
|---|---:|
| native | 0.615 |
| interpreter | 0.357 |
| jit | 0.353 |

One successful cold build per mode, with separate empty Cargo artifact directories. Engine bootstrap, the preinstalled toolchain/sysroot, and OS file-cache coldness are excluded.

| Mode | Cold command seconds |
|---|---:|
| native | 21.812 |
| interpreter | 16.436 |
| jit | 16.827 |
