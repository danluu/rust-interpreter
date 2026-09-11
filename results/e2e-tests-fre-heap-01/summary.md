# Existing fre test: edit to result

Full commands, including launcher and Cargo; five test-source edits. Original seven codec boundary roundtrips preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.

| Mode | Median edited command seconds |
|---|---:|
| native | 1.342 |
| interpreter | 0.714 |
| jit | 0.719 |

One successful cold build per mode, with separate empty Cargo artifact directories. Engine bootstrap, the preinstalled toolchain/sysroot, and OS file-cache coldness are excluded.

| Mode | Cold command seconds |
|---|---:|
| native | 7.038 |
| interpreter | 4.296 |
| jit | 4.422 |
