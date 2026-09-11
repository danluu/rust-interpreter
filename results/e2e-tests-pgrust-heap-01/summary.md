# Existing pgrust test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original 100,000-iteration roundtrip loop preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median edited command seconds |
|---|---:|
| native | 0.635 |
| interpreter | 0.912 |
| jit | 0.630 |

One successful cold build per mode, with separate empty Cargo artifact directories. Engine bootstrap, the preinstalled toolchain/sysroot, and OS file-cache coldness are excluded.

| Mode | Cold command seconds |
|---|---:|
| native | 1.161 |
| interpreter | 0.930 |
| jit | 0.630 |
