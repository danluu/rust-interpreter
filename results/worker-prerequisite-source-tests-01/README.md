# Worker and MonoItem prerequisite source tests

All 159 Python tests passed at source `bd3033633ad680d38954f5ccf948ecb8f1548eb3`
(1.104 seconds reported by unittest), with no skips. The first run at source `759498fe9e187ada955eb362e374287390682cb5`
completed all 159 tests with one error: an older publication mock rejected the
new qualification-policy keyword. The second run changes that mock to require
and assert the correct default policy; its publication-failure assertions remain.
Both attempts, including the failed run, are retained. The combined selection
retains all 16 prior compiler, launcher, standard-source, screen and assessor
suites and adds the five worker/publication suites. It includes the corrected
raw/tagged MonoItem evidence check and worker lock, copied-fixture and frozen
proof checks. No Rust build or benchmark ran in this test execution.

The archive contains both attempts' exact tested Python sources, worker fixture inputs,
`owned_stage.py`, shared public build helper, raw test output, child and external
supervisor receipts, and both task scripts. Source snapshot hashes were checked
against the test receipt, and every archive member was rehashed under the
canonical workload lock. Archive headers are normalized; payload bytes are
retained exactly. Public tool build and real 30-command worker qualification
remain separate prerequisites before the 27-command performance screen.
