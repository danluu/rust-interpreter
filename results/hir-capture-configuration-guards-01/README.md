# HIR capture driver configuration guards

Both Python tests passed with no skips against source commit `115fbd80bf82ed4a6298691ccf68814b4585bcf0`. They check that newly created Cargo configuration files change the frozen guard and that configuration file/directory symlinks are rejected. The exact driver, four capture-only inputs, README, test, process helpers, and test supervisor were frozen and remained unchanged.

The archive contains the raw test output, command and environment, Python identity, process receipts, exact source snapshots and supervisor records. Every member was read back and checked. Originals remain in the test worktree. The archive supervisor completion is retained separately in `archive-supervisor.json`.

This qualifies only these two source-configuration guards. No plan was materialized, compiler checkout created, compiler built or checked, or benchmark run. It makes no HIR reuse or performance claim.
