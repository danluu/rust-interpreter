# C9 independent raw timing audit

PASS. This audit read the completed fixed panel and recomputed its results; it did not rerun any timing, import a project module, execute the controller, or change measured sources. Exact floating-point recomputation used the pinned CPython 3.14.7 executable with `-I -S -B`.

The result is limited to the public `std_mir_readmission.validate` component on two immutable synthetic 26-artifact fixtures. It does not establish whole-build, exporter, launcher, runtime, or holdout performance.

## Verified raw evidence

- Exact frozen 92-call schedule: 4 parity, 8 warmup, 80 measured; 20 AB/BA pairs per case, with all warmups before measurements and no extra samples.
- All 184 distinct child PIDs have matching planned/start/terminal receipts, 368 current log proofs, exit code zero, exact parent PID 35390, empty stderr and no settlement/observer errors. Recorded child intervals do not overlap. `wait4` CPU sums, wall duration and RSS are positive and match every result row.
- All 92 raw stdout reports equal their retained report files and result rows; every config, command, environment, stage receipt hash, actual one-call/None outcome, source selection and before/after fixture proof reconciles. The JSONL rows equal the complete result rows.
- Both prerequisite suites retain 24 successful tests: actual CPython 3.14.7 enables the candidate guard; actual CPython 3.9.6 disables it. The fixture qualification retains three successful baseline calls and two settled children.
- All 487 fixed/project input proofs remain byte- and stamp-identical; the two 189-file project inventories match. The complete sealed 68-entry fixture tree is unchanged, including ready manifests and the actual published receipt.
- The private warmed cache and loaded dependency proofs are unchanged. Every reported cached module resolves to retained private bytecode with a valid header/source binding; parity/measured commands use `-B`, and only the 8 fixed warmups permit bytecode writes.
- All 200 individual ratios, every reported median/geometric mean/order stratum/win count, and all 16 frozen adoption gates recompute exactly under the pinned interpreter. All 16 gates pass; component CPU wins are 20/20 in each case.

Minimum recorded memory admission: 63%. Minimum recorded child disk headroom: 25605345280 bytes (23.846836 GiB), above the 16 GiB floor. Every API admission follows its own memory probe and is less than 20 seconds old at launch. The cache contains 30 files / 620235 bytes in 25 directories; 49 dependency files remain bound.

| Case | Component CPU ratio | Component wall ratio | Process CPU ratio | Process wall ratio | RSS ratio | CPU wins |
|---|---:|---:|---:|---:|---:|---:|
| matching_saved_stamps | 0.767484957689267 | 0.766134095513151 | 1.00438606564012 | 1.00477172777375 | 0.999963271727781 | 20/20 |
| matching_device_readmission_receipt | 0.860640409820315 | 0.86102222574284 | 0.999594692576712 | 1.00187126530546 | 0.99917077217108 | 20/20 |

## Identities

- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/run-screen.py` — 40058 bytes, SHA-256 `c7ec414e00955014fb66afa300ba29cbb6d4c270db9f82d99a6d438953c49665`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/timing-driver.py` — 13147 bytes, SHA-256 `770d3c204c6be5f5c4acb310e2ff1923d8c1702b86a587acbd1b5253e49becf9`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-bindings.json` — 88557 bytes, SHA-256 `1e93493bc152886005cd077545d663cca2450c959f0b2262c1f4d9007945525f`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/decision-plan.json` — 14882 bytes, SHA-256 `a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/unit-screen-01/result.json` — 416054 bytes, SHA-256 `26d9bb17cd6abf6839c22a7e795af39c868e0c8657ae032b98f0c3206dc29a9a`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/compatibility-screen-01/result.json` — 430613 bytes, SHA-256 `3157f8de282d7af4d43cc218557341273d9a331b7a007158fef341628923a843`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/fixture-qualification-01/result.json` — 506888 bytes, SHA-256 `759b5a85fa7e40e5a8e126dc87c070e93a52ce4e68ccff9b4d8ec0498321ab0a`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/fixture-qualification-01/fixtures.json` — 144054 bytes, SHA-256 `05e1b708626d285a1186730d3813ac5273c3cbbc89ba1992d07e48c288fcd656`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/result.json` — 4682560 bytes, SHA-256 `9220089e82172c4c9748a7e81eff7b5696265986b2829eb0c72e2f98293048ec`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/inputs-before.json` — 291139 bytes, SHA-256 `be9535149ebbfa4d36aafe87a8d123cd9d3b6d27454e43214c1cb89d94d63e4a`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/inputs-after.json` — 291139 bytes, SHA-256 `be9535149ebbfa4d36aafe87a8d123cd9d3b6d27454e43214c1cb89d94d63e4a`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/dependencies-frozen.json` — 30929 bytes, SHA-256 `8b0b5b5733b6c8a029881fc334bd69a0c7274748b80cf7b7ceb12ea4d736a68e`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/bytecode-cache-frozen.json` — 49028 bytes, SHA-256 `9dada7324b572c3082b293139fb6b46f32c689c9a945ad41846a4079ea18fa68`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/bytecode-cache-after.json` — 49028 bytes, SHA-256 `9dada7324b572c3082b293139fb6b46f32c689c9a945ad41846a4079ea18fa68`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/fixtures-before.json` — 25948 bytes, SHA-256 `6daab41e051ff279da46f7320a4ad0213d25a72818f731d96091f4df6c6f7b11`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/fixtures-after.json` — 25948 bytes, SHA-256 `6daab41e051ff279da46f7320a4ad0213d25a72818f731d96091f4df6c6f7b11`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/schedule.json` — 12569 bytes, SHA-256 `9ce504f17b8bc9910265095317c65e3883736f78457c53af24b48240b9b0815f`.
- `/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe/screen-01/samples.jsonl` — 3458038 bytes, SHA-256 `84ff17be3d3ac75b9eb3478af1f8184f21f9a4e11782a76cc163846a81779533`.

The immutable raw result contains all 92 driver reports, all 184 child records and all 200 ratios; accompanying raw logs, configs and terminal receipts remain in `screen-01`. This audit confirms recorded evidence and current bindings, not an independent reconstruction of historical kernel accounting.
