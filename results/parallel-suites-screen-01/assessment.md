# Two isolated workers pass the runtime screen

The same custom VM runs the original selected token, folded and pgrust suites
with one or two workers. Six alternating pairs include process startup and all
JIT preparation; no LLVM or external guest engine is used. Each worker owns its
JIT on its creating thread and every test starts with fresh guest state.

| Original suite | Tests | Median paired wall ratio | CPU ratio |
| --- | ---: | ---: | ---: |
| fre token | 12 | 0.582200 | 1.037618 |
| fre folded | 18 | 0.967498 | 1.031065 |
| pgrust hash | 4 | 0.978473 | 1.121607 |

Token improves41.8% wall with3.8% more CPU, passing the predeclared20% wall and
20% CPU gates. Folded passes its guards. Pgrust adds about2ms CPU; the fixed
10ms absolute allowance applies to this approximately17ms saved process.
All36 measured commands execute the original assertions. Folded/pgrust logical
counts and memory remain exact. Token uses normal OS entropy, so its counters
are recorded rather than forced to match independently randomized executions.

The prior serial qualification passes seven exact recorded per-test inputs and
nine whole-suite commands, comparing the retained/new serial VMs and concurrent
outcomes. The first whole-suite controller stopped on an incorrect assumption
that folded process entropy was zero; it consumed one16-byte read, with exact
guest counts. That failed run remains preserved. The corrected qualification
passed before this screen; there was no failed-screen retiming.

Source aec0127 / tool fe9dcae0; VM SHA256
209a29779f6c22de4015dd7c90e6cb0cd089f2a216dc6af7ea2068957d5fb8b6.
All365 Rust workspace tests pass in each host profile, with one ignored.
The launcher and concurrent native control pass56 Python tests.

This is saved-artifact runtime evidence. It excludes checking and export and
does not establish complete-command improvement over either custom or native
compilation. Keep the default at one worker. Next run the fixed real-edit
comparison, including concurrent native processes and strict source restoration.
The recent exact-name native controls were serial; ordinary libtest concurrency
must not be conflated with those recorded commands.

[Raw-bound summary](summary.json),
[serial qualification](../parallel-suites-serial-02/summary.json),
[fixed changed-source plan](../../benchmarks/experiments/parallel-suites/WORKFLOW.md).
