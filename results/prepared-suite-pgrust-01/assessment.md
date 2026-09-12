# Isolated pgrust source-edit commands pass; preparation savings are too small to change latency

All 21 primary commands, seven Cargo-check controls and four restored-source
commands pass. Four original hashfn tests run once per command with independent
state; the deliberate wrong production edit fails the same tests in native,
fresh JIT and prepared JIT modes. Tests are unchanged, sources restored, and all
14 primary plus two restored custom artifacts match between modes.

| Five edited commands | Median wall time |
| --- | ---: |
| Native build + four separate test processes | 0.697 s |
| Export + fresh JIT per test | 0.511 s |
| Export + shared prepared JIT | 0.514 s |

The median paired prepared/fresh ratio is 1.0084 wall and 1.0076 CPU.
This one-cycle qualification establishes no latency improvement. Median custom
execution falls from 19.09 to 17.11 ms, and compilation during execution falls
from 3.60 to 2.04 ms. Constructor preparation falls from 0.495 to 0.139 ms.
The saved work is small beside the complete command. Native's median build is
0.441 s and its four test-process invocations total 0.234 s. These nested medians
must not be added to reconstruct the complete-command median.

Cold original commands were 1.246 s native, 1.078 s fresh and 0.537 s prepared,
with native/fresh/prepared fixed order and separate fresh Cargo targets. This
single unbalanced cold observation does not isolate a preparation benefit;
shared tools, standard metadata and filesystem caches were already prepared.
Native process isolation differs from ordinary shared-process libtest. Neither
these native costs nor the custom costs replace prior ordinary-batch timings.

Source a8f4ee2 uses the 5b3268c/5b26d967 custom runtime with retained exporter and
wrapper. All 320 debug and release workspace tests pass (one ignored), and 36
Python harness tests pass. Keep the runner optional. Next execute the predeclared
token and folded workflows, and report their outcomes even if prepared loses.
The outstanding full-harness features include ignore, should-panic, unwinding,
threads and complete OS/FFI support.

[Protocol](../../benchmarks/experiments/prepared-jit/WORKFLOWS.md),
[compact measurement](isolated-assessment.json), [control verification](verification.json).
