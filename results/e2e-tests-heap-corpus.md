# Existing-test corpus with heap and SIMD support

All five runs use the same custom-engine build, ordinary rustc frontend checking,
and the pinned corpus revisions. Each complete command includes Python startup
where applicable, Cargo, compilation, and the selected existing test. Every engine
rejected a deliberately wrong added assertion before five successful test-source
edits were measured. The original test workloads were preserved.

These qualify selected existing tests in real workspaces, not whole applications
or test suites. Five samples on a shared host do not provide a confidence interval.

| Project | Native edited command | Interpreter | Custom JIT |
|---|---:|---:|---:|
| [pgrust](e2e-tests-pgrust-heap-01/summary.md) | 0.635 s | 0.912 s | 0.630 s |
| [fre](e2e-tests-fre-heap-01/summary.md) | 1.342 s | 0.714 s | 0.719 s |
| [nushell](e2e-tests-nushell-heap-01/summary.md) | 0.615 s | 0.357 s | 0.353 s |
| [ruff](e2e-tests-ruff-heap-01/summary.md) | 3.831 s | 2.526 s | 2.695 s |
| [rg-aot](e2e-tests-rg-aot-heap-01/summary.md) | 0.480 s | 0.171 s | 0.171 s |

Each engine also ran one successful first build in its own empty Cargo artifact
cache. Tool installation/bootstrap, the preinstalled sysroot, crate downloads,
and OS file-cache coldness are excluded. These are artifact-cold observations,
not repeated fully cold-machine measurements.

| Project | Native first command | Interpreter | Custom JIT |
|---|---:|---:|---:|
| pgrust | 1.161 s | 0.930 s | 0.630 s |
| fre | 7.038 s | 4.296 s | 4.422 s |
| nushell | 21.812 s | 16.436 s | 16.827 s |
| ruff | 57.633 s | 25.266 s | 25.508 s |
| rg-aot | 3.653 s | 2.728 s | 2.730 s |

The custom path lowers only the selected reachable execution graph and avoids
native application linking. Its compilation savings cannot be attributed solely
to JIT code emission. The JIT helps pgrust's long scalar loop; interpretation is
competitive for the short tests. Ruff's JIT has a higher full-command median in
this run, although its execution-stage difference is much smaller and compiler
time varies.

Pgrust also exposed a regression after adding the heap: interpretation rose from
about 0.362 s to 0.435 s of execution, and JIT from about 0.146 s to 0.155 s. The
complete JIT/native commands are approximately tied here. The next experiment
inlines the small memory-selection helpers and measures the full edited command
again. Do not retain the earlier pgrust speedup as a claim for this build.

Private rg-aot source, commands, and detailed logs remain under `.work`; the
linked report exposes aggregate timings and source hashes only.
