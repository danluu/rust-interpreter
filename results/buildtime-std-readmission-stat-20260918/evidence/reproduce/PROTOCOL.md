# C9 fixed public validation screen

This is the implementation protocol for the decision frozen in decision-plan.json, SHA256 a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b. The earlier PROTOCOL-DRAFT.md remains intact at SHA256 435e12cfef7b2e09311f6c05d459ce22dfa5fd2fb8cc2b2ec0197b6b1794d7f8. Its pending source, runtime and qualification statements are historical. This protocol binds the completed correctness and fixture stages without changing any numeric gate, case, clock or schedule.

Both source trees descend from f38004cbd3392b5a6763f920d80801826bbde77c. Baseline is /Users/danluu/dev/rust-interp-allocation-decoder-publication-20260918; candidate is /Users/danluu/dev/rust-interp-std-readmission-stat-20260918. Exactly two Python sources differ: scripts/std_mir_readmission.py and tests/test_std_mir_readmission.py. The production change uses one stat on CPython 3.14 POSIX; other runtimes retain the original path. All downstream file hashing, descriptor checks, receipt validation and final checks remain.

## Completed prerequisites and bound inputs

The following retained receipts are prerequisites, not performance samples:

- Primary CPython 3.14: unit-screen-01/result.json, SHA256 26d9bb17cd6abf6839c22a7e795af39c868e0c8657ae032b98f0c3206dc29a9a. Both arms passed the same twelve semantic methods, 24 executions with four settled children.
- Actual installed CPython 3.9.6: compatibility-screen-01/result.json, SHA256 3157f8de282d7af4d43cc218557341273d9a331b7a007158fef341628923a843. The same twelve methods passed on both arms, another 24 executions and four settled children. Candidate guard was false, exercising the original fallback.
- Actual baseline fixture preparation: fixture-qualification-01/result.json, SHA256 759b5a85fa7e40e5a8e126dc87c070e93a52ce4e68ccff9b4d8ec0498321ab0a. One preparation child and one memory admission settled successfully; three actual public validate calls returned None without output.
- Frozen fixtures.json: SHA256 05e1b708626d285a1186730d3813ac5273c3cbbc89ba1992d07e48c288fcd656.
- Common timing-driver.py: SHA256 770d3c204c6be5f5c4acb310e2ff1923d8c1702b86a587acbd1b5253e49becf9.

screen-bindings.json, SHA256 1e93493bc152886005cd077545d663cca2450c959f0b2262c1f4d9007945525f, binds the base commit, exact roots, all 189 Python source files per arm, the two changed files, the stdlib root, and 109 fixed files. Fixed files include the v3 patch/source evidence, applied manifest, correctness runners/drivers/runtime sources and successful receipts, preparation sources and evidence, exact fixture descriptor, and timing driver. They also include the preparation child's observed dependency sources. All fixed entries contain byte count and SHA256. The controller is excluded to avoid a hash cycle; it records and rechecks its own source identity before/after execution. Frozen-plan stage placeholders are completed by these separate bound receipts rather than editing the decision.

## Scope and immutable fixtures

Both arms use exactly the same absolute fixture paths under fixture-qualification-01/fixtures:

1. matching_saved_stamps: 26 regular files with the current saved stamps, returning through the current==original branch without a receipt.
2. matching_device_readmission_receipt: the same 26-name layout in a second owned tree, with recorded devices uniformly current device plus one and an existing exact baseline-created readmission receipt.

Each file is a deterministic 1 KiB synthetic payload. The names and their order reproduce one retained 26-artifact ready manifest; payloads are not valid Rust metadata. Only the old 8,457-byte ready JSON was read. Its 112,958,025-byte metadata payloads were neither opened nor copied. This screen exposes the public reused validation routes; it does not measure validation of 113 MB of real compiler metadata.

Preparation called the actual baseline API once on matching stamps, then twice on the second tree to create and reuse its receipt. No validation, filesystem stamp, hashing or receipt function was mocked. The resulting complete parsed manifest, exact ready/receipt text, and immutable inventories are recorded in fixtures.json. Payload files, manifests, receipt and directories are sealed. There are at most 256 entries, 64 KiB per file and 1 MiB total. No fixture is reset, overwritten or regenerated between arms or rounds.

The controller and each driver compare complete snapshots against qualification, including regular-file bytes/SHA256 and [device,inode,mode,size,mtime_ns,ctime_ns,nlink] stamps plus directory identities. Driver checks run before and after the component clock. Its parsed input must remain unchanged, actual return must be None, and captured API output and error must be empty. The full descriptor and selected production source are rechecked after the API call. Snapshot reads use the reviewed bounded no-follow/nonblocking descriptor checks. Fixture creation and the first complete-hash recovery are never timed.

## Fixed sequence and bytecode regime

The screen contains exactly 92 fresh API-driver processes, each with one memory-admission process:

- Four parity drivers: AB once per case, all before warmups; no performance statistics use these calls.
- Eight warmup drivers: ABBA for each case, all before measured calls.
- Eighty measured drivers: twenty pairs per case. Even rounds visit cases forward and run AB; odd rounds reverse case order and run BA. Each case therefore has ten AB and ten BA pairs.

This is 184 screen children. The completed fixture stage adds two; correctness adds eight separately. Each driver calls actual std_mir_readmission.validate exactly once. No in-process repeat loop, retry, replacement, outlier removal, extra round or adaptive warmup is allowed. Every raw observation remains recorded.

Timing uses the pinned Homebrew CPython 3.14.7 executable with -I -S and an explicit -X pycache_prefix inside a fresh screen output. Preparation's separate qualification prefix stayed empty and is not reused. All parity drivers use -B and leave the new timing prefix empty. Only the eight warmups may populate it. The controller freezes a bounded cache inventory, exact cache bytes and source/header correspondence after all warmups. Measured drivers use -B, consume the existing cache and must not change its inventory. There is no global or worktree bytecode write.

## Clocks and fixed adoption decision

Module import, descriptor/manifest parsing, full fixture snapshots, provenance reporting and compact output are outside component clocks. The driver measures process_time_ns and perf_counter_ns around the single actual public validation call, including its normal Python call/exception bookkeeping. An audit hook rejects child launches. Parent wait4 user+system CPU, wall time and peak RSS cover the whole fresh driver, including imports and all those checks. Whole-process guards remain required even if this small component improves.

Compute unrounded candidate/baseline ratios for all twenty fixed pairs in each case. Retain raw samples, per-pair ratios, arm medians, absolute paired deltas, strict CPU wins and separate AB/BA geometric means. Every one of these eight gates must pass for each case:

- Component CPU geometric ratio <= 0.95.
- At least 15 strict component CPU wins out of 20.
- AB component CPU geometric ratio < 1.
- BA component CPU geometric ratio < 1.
- Component wall geometric ratio <= 1.
- Whole-driver CPU geometric ratio <= 1.01.
- Whole-driver wall geometric ratio <= 1.02.
- Whole-driver wait4 peak-RSS geometric ratio <= 1.05.

All sixteen numeric gates and all source, semantic, fixture, cache, resource and settlement requirements are mandatory. Procedural success is separate from adoption. Any failed, missing, mismatched or inconclusive performance requirement parks the candidate; no helper-only, route-only or relaxed-guard fallback is permitted. Do not rerun a valid panel to seek a different result.

## Resource and interpretation limits

The controller holds the shared exclusive benchmark lock across the fixed screen. Each child receives a fresh direct 16 GiB disk admission; every API child requires a fresh >=30% memory reading. A five-second read-only observer records disk status while children run. Exact PID, argv, cwd, environment, start time, logs and terminal wait4 receipts are retained, and child settlement occurs in finally even if a record operation fails. No peer process is signaled or altered. This is a bounded Python/filesystem category; Rust builds retain the separate 32 GiB gate.

No compiler, Cargo, guest execution, network request or large metadata copy is part of this screen. If all gates pass, the supported claim is limited to these two public validation routes on synthetic 26-path fixtures. It is not a measured whole setup, build, export or unknown-holdout speedup. The proposal's source review and cross-version tests define its semantic scope; this fixture panel does not add a claim of identical observations under concurrent path mutation.
