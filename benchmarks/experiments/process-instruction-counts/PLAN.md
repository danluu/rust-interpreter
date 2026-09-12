# Whole-process retired instruction diagnostic

The first Instruments probe completed the original native exhaustive token
test. Its default guided CPU Bottlenecks configuration exposes cycles and
ratios, not a validated retired-instruction total. Raw counter arrays lack an
established event mapping; do not infer one from their positions or sum
overlapping sample windows.

Use macOS's existing per-process accounting instead. Apple's
[Recount documentation](https://github.com/apple-oss-distributions/xnu/blob/main/doc/observability/recount.md)
identifies retired instructions in its CPU accounting and exposes them through
proc_pid_rusage. Its [process lookup](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/proc_info.c)
accepts an exited, unreaped process; [resource accounting](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_resource.c)
returns cached final statistics. Installed SDK headers declare RUSAGE_INFO_V4
with instructions and cycles. Verify this behavior on the current host rather
than assuming a kernel-source version matches the installed OS.

A small diagnostic launcher creates exactly one child with posix_spawn and
records its PID, parent and launch command. It waits for natural exit using
waitid(WEXITED|WNOWAIT), queries that exact child twice, and reaps it with
waitpid. Require equal final counters, nonzero start/exit timestamps, matching
exit outcomes, and positive instruction/cycle counts. No attachments, signals,
injected libraries, privilege changes, settings changes or other processes.
Compile the host launcher with the installed C compiler; guest execution
remains the existing custom VM and direct AArch64 emitter.

Qualify accounting on 200,000- and 2,000,000-iteration volatile loops and an
intentional exit-seven child. The longer loop must retire more instructions;
these are API checks, not performance evidence. Preserve zero/error results
and stop if the counters are unavailable; no fallback service activation.

Then run three alternating native/JIT pairs of the same original exhaustive
token assertion. Bind native to the completed restored anchor build and its
previous probe's binary digest. Bind custom execution to qualified integrated
tool49746a22 and the exact original RBC/catalog. Use ordinary OS entropy and
one test per process, with fixed VM limits. Verify original assertion outcomes,
catalog identity and unchanged inputs. Never execute the held fixed-clear VM.

Scope is whole target process lifetime: native includes loader/libtest setup;
custom includes loader, RBC decode, analysis, code generation and guest test
execution. It excludes the parent launcher. It is not a pure guest count, a
same-entropy differential check, or a complete Cargo edit/build/test benchmark.
Instruction inflation and cycles/instruction guide the next implementation;
they cannot establish a development-loop win or replace edited-command gates.

Serialize compilation and all child launches under the existing benchmark
lock, with45-second admission and3GiB disk floor. Run once after Nushell native
calibration. Freeze source, tool, artifact, plan and controller inputs. Keep all
three pairs and failed observations; do not retry to obtain a preferred ratio.
