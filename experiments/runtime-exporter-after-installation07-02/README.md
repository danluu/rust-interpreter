# Exporter with complete dyld event parsing

This successor preserves the original metadata, build and frontend recipes:
36 metadata commands, one ordinary locked/offline release Cargo build with two
jobs plus six tool checks, and 34 frontend commands containing all 18 controls
and nine diagnostic comparisons. Sources, target, work directories and packet
are independent of attempt01.

Attempt01 completed every metadata command successfully, then its load-only
dyld reader rejected delayed-load transitions. The replacement retains every
byte and models both transition directions using a unique previously reported
library name and the actual child process ID. The admitted compiler driver must
remain active. All 24 controls passed, including both saved failing streams.
No compiler or application was run for those parser controls.

Source review caught two old relative directory constants before execution;
their unexecuted drafts remain in `pre-relative-route-review`. Preparation03
then stopped because a normal merge reapplied negative sparse-checkout rules
to five old VM proof files. The exact five paths now have positive sparse
rules. Failed output and logs remain retained; preparation04 passed after
restoring the same Git bytes. Root and independent packet readbacks passed.

The direct launcher normally waits the existing supervisor. It persists that
wait before reading the supervisor terminal, and separately requires a
successful controller exit. The ordinary shared workload lock remains inside
the phase controller. Resource checks retain the 16/9/8 GiB thresholds and
Cargo jobs=2; there is no claim of a CPU, wall-time or memory limit.

Current metadata/build/frontend/publication source closures contain 11, 15,
20 and 25 files. Stage controllers authenticate their selected source closure
before local imports. Publication uses the existing three-tool format and
ordinary installed-tool readers. Application correctness and performance
remain separate later steps.

Evidence:

- [Closed metadata01 failure](../../results/runtime-exporter07-metadata-failure-01/STATUS.md)
- [Passed parser controls](../../results/runtime-exporter-dyld-parser-test-01/README.md)
- [Fixed prospective Ruff screen](../hir-options-hash/ruff-screen-01/PROTOCOL.md)

Historical manifests and handoffs retain their status at creation. Actual
closed result records establish which subsequent stages have run.
