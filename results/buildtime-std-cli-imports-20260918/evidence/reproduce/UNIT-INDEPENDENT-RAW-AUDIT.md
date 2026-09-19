# C13 unit raw audit

PASS. This audit independently reconciled the retained run with its frozen source and current file identities. It did not rerun tests, import a controller/project module, query any compiler, acquire a workload lock or control any process. I authored the unit harness; independence here is from the root execution/raw-result interpretation, not a separate harness author. The separate source review remains the independent reviewer’s work.

The raw result is `unit-screen-01/result.json`, 2,583,598 bytes, SHA256 `8cc032cc67a9b9880b130cb0449171f820982868bdf40190ca2be17946b670a0`. Frozen controller `b1af3370ff5b81863a1197dc24ea701de0716030b66572daabd5add8f2e41fee`, driver `d1546542fdaa7287320468bd31e63022cfa279d9ac6588a65c5fc16f7d7a5ebf`, and manifest `db14ba649b5f51f9533e950e731a0fe3e5ecb4bf33a6403fde6b10e5b0702755` all match current bytes and the recorded bindings.

All 21 exact source-counted IDs passed: 8 selection-routing, 6 custom-compiler launcher and 7 custom-Cargo tests. The raw unittest stderr has precisely those 21 `ok` lines, `Ran 21 tests in 0.627s`, and final `OK`. Full child-report JSON equals the report embedded in the result and matches its retained SHA/stamp. The report has no failures, errors, skips, expected failures, unexpected successes or actual-process audit events. The canonical candidate std_mir source and all three test-source proofs match. All 18 recorded project modules belong to the candidate’s frozen inventory; all 170 runtime module records match the frozen Python closure. The actual child reports CPython3.14.7.

Exactly two children are retained: memory query PID 42052 and unit driver PID 42053, both parent 34115, both exit 0 with no controller error, no TTY and the expected owned cwd/environment. Planned/start/terminal JSON reconciles exactly with each final record; all four log proofs match current bytes and identities. The records include complete user/system CPU, wall and peak RSS evidence, and their intervals do not overlap. The driver command is the pinned executable with `-I -S -B`, the explicit private prefix, exact driver and report path. The 51% memory admission immediately precedes the unit launch by less than 20 seconds. Both launch disk readings and both observer samples exceed 16 GiB; minimum recorded free space is 23.924732 GiB. No continuation or child replacement appears in the retained schedule.

All 2,360 before/after input records are equal and still current: 2,352 regular-file byte/SHA/identity proofs plus 8 exact symlink identities/text/resolutions. This includes all 190 candidate Python sources, all 189 baseline files used only as read-only provenance, and the 1,955-file Python/native closure. The only Python arm differences are the intended std_mir source and new selection test. Both source filename inventories remain exact. The run’s inputs/test-inventory files equal the corresponding result data. The private pycache and unit TMPDIR are currently empty, agreeing with the driver. All 16 original stage files were checked and are listed below; no retained stage file was changed.

The first audit command ef1b04 completed all verification assertions but failed formatting this note because its literal percent sign was unescaped. It wrote no note or stage file. The corrected source-only writing command rechecked all 2,360 current bindings before recording this result. No test/workload retry occurred.

This qualifies synthetic Python routing and selected-tool correctness. It does not establish build, export, startup or holdout performance, and no real Cargo/compiler/VM subprocess ran inside the unit test process according to the installed audit hook.

Original stage file hashes:

- `candidate-selection-memory-observations.jsonl` — 133 bytes, `37688323aa7bf6d0d890ea4205e22a93ccf4c820fbc776673e964db0bc3708df`.
- `candidate-selection-memory-planned.json` — 667 bytes, `3ca76310c99d5f44b9c8d6cebce137b7de37b47fc4e5a34f0887e26b8714b51c`.
- `candidate-selection-memory-start.json` — 769 bytes, `914693581e6760060118a30ad5db9fa03d23a0957c841ded045d363d90d9dc94`.
- `candidate-selection-memory-terminal.json` — 1910 bytes, `d1b5948bc366a4b7e68b54262dfa1b4603efc84aa4e9c3cb48f72ca419f82a43`.
- `candidate-selection-memory.stderr` — 0 bytes, `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- `candidate-selection-memory.stdout` — 110 bytes, `839ae6b5c31b6b93509a497e07daaea92dda22a6765a2e2734f23f60e2d2f9e7`.
- `candidate-selection-observations.jsonl` — 133 bytes, `e24e5b8daf1f2b97d4a33e4d94109c20ddfc62261f2a685d68de652467dc04ea`.
- `candidate-selection-planned.json` — 1407 bytes, `ee320cd56ad1ad9405d6e287dce0079f64b552a0ef7d5ae7af881b33884152ab`.
- `candidate-selection-start.json` — 1507 bytes, `5c0178b25e17c712de5387efda1cfd7638d3032da8fa03f9f33bb530831c14c1`.
- `candidate-selection-terminal.json` — 2657 bytes, `41e49ffe11c303a9c71916a34b1e46dc6d13929cb78652acc55f4ec2955a30d6`.
- `candidate-selection-tests.json` — 63011 bytes, `463e8b9aff88c3587ae2fb04622774a5be284bdc1e2c8807bfab7134acfccb88`.
- `candidate-selection.stderr` — 4209 bytes, `35ff185f58da0b86e523f726f243d28f73ea5a95f6cc0bbb8d7a88b902f474eb`.
- `candidate-selection.stdout` — 235 bytes, `6f61d956364a0bed3944eb98cd19bfd48a66df05682a11bd8c28cbb57238290e`.
- `inputs.json` — 1250390 bytes, `274d632d5081e898be33908dd4b95f7633b3a456977b893de095ec8e31f4691d`.
- `result.json` — 2583598 bytes, `8cc032cc67a9b9880b130cb0449171f820982868bdf40190ca2be17946b670a0`.
- `test-inventory.json` — 6152 bytes, `8b330e520667edd4f297cb673a583b450b35d711fc60220a4dc38af8707833ea`.
