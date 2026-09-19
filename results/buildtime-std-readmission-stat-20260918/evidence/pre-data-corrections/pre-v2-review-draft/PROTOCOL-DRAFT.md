# C9 proposed two-case validation screen

This is a source-only measurement design, not a frozen decision or an execution request. No C9 fixture, project import, test, API call or timing has run. The candidate tree exists but the parent is reviewing the source proposal. Applied-source, runtime, unit and controller bindings remain UNBOUND. Finalize source review and freeze the numerical plan before any candidate execution.

Use two cases, both with the retained 26-artifact path layout: already matching saved stamps, and an existing exact uniform-device readmission receipt. These are the two recurring success paths through the actual public std_mir_readmission.validate called by ready std-MIR reuse. A one-artifact variant adds little production evidence and doubles the small-call panel, so it is omitted.

fixture-shape-draft.json binds the owned ready.json (8,457 bytes; SHA8e16a62a0a0339fe13117e74fec306504a64bb2377c460edccca9064f9d0d3a3), its 26 paths in original order, and its recorded 112,958,025 metadata bytes. Only that JSON was read. None of those real metadata payloads is opened or copied.

## Honest bounded fixtures

Create two new canonical owned fixture trees with the same relative artifact names and iteration order. Every payload is a deterministic synthetic 1 KiB regular file, derived from its relative name; each tree therefore has only 26 KiB of payload. These are deliberately synthetic blobs, not valid Rust metadata. The reused API only inspects filesystem stamps, and in the receipt case it also reads its small manifest/receipt JSON. Real metadata contents and logical sizes are not necessary to expose the duplicate-stat operation. Results must identify this synthetic 26-path scope and must not claim a measured 113 MB real metadata validation.

Before writing, apply the usual 16 GiB/30% admission. Bound preparation to256 entries,1 MiB total and64 KiB/file. Keep the exact same absolute fixture paths for both arms. Create payloads with final read-only file modes before collecting the stamps. Each manifest includes actual payload hashes and an explicit synthetic-fixture label.

One preparation child performs exactly three actual baseline public API calls, without mocking stat, validation, hashing or receipt construction:
1. Validate the first tree using its actual current saved stamps; it should create no receipt.
2. Validate the second tree with each saved device number set to the real current device plus one, and every other stamp field exact. The real baseline validator hashes the small payloads and publishes its own receipt.
3. Validate that second tree again through the receipt reuse path and verify the receipt and manifest bytes are unchanged.

Then seal the ready files, receipt and directories, and freeze a bounded full inventory of bytes, modes, stamps and exact API inputs. Parent and both arms must verify that inventory, exact None results and absence of unexpected API output. No fixture is reset or regenerated between arms, rounds or cases. Freeze the prepared current device observation; a later filesystem identity change rejects the screen.

## Correctness before timing

The pending source proposal has seven unchanged existing methods and four meaningful new semantic methods, eleven per arm (22 test executions in two test children plus two memory admissions). Preserve actual module selection for each arm and require all exact IDs to pass without skips. The existing complete-hash/readmission/mutation cases still qualify paths not timed here. New cases cover file types, followed symlinks, cross-version OS-error policy and exception precedence; they do not count implementation calls.

The first AB pair for each timed case is retained parity qualification. It must use the actual validate function, match the None outcome and all relevant artifact/ready/receipt identities, and produce no API output. It is not part of the performance statistics. All subsequent calls must pass the same outcome/immutability guards. Runtime errors and partial attempts are retained, not repaired or replaced.

## Fixed proposed panel

Use pinned Homebrew Python3.14 and one new common private bytecode prefix, explicit -I -S -X pycache_prefix. Preparation and all four parity drivers use -B. Exactly eight warmups (ABBA per case) then populate the cache; freeze its bounded inventory and source correspondence. The 80 measured drivers use -B. Keep module loading and fixture-JSON reading outside the component clock; make no imports/test mocks part of the production API.

Twenty rounds each visit both cases, forward order on even rounds and reverse order on odd rounds. Each case runs AB in even rounds and BA in odd rounds:20 pairs per case,10 per order stratum. Exactly one actual validation call runs per driver.

The panel is4 parity+8 warmup+80 measured=92 API drivers, each with its own memory-admission child (184 screen children). Adding the one preparation child and its memory check gives186. The four unit-stage children are separate. No additional case, repeated call inside a sample, retry, discarded sample, replacement, adaptive warmup or extra round is permitted.

Component CPU and wall surround the actual validate call only. No child process runs inside that component. Parent wait4 CPU/wall/RSS cover the full fresh driver, including imports, proofs and compact reporting. Keep source and reporting work symmetric and retain all process guards; a small component gain cannot excuse an unqualified whole-process regression.

## Proposed gates to freeze before data

For each of the two cases, all eight gates are proposed:
- Component CPU geometric candidate/baseline ratio <=0.95.
- At least15 strict component CPU wins among20 pairs.
- AB and BA component CPU geometric ratios each <1.
- Component wall geometric ratio <=1.
- Full-process CPU geometric ratio <=1.01.
- Full-process wall geometric ratio <=1.02.
- Full-process wait4 peak-RSS geometric ratio <=1.05.

This is16 numerical gates across the two cases. Five percent is a proposed minimum component gain for a direct syscall reduction, not a fitted threshold. Report unrounded paired ratios, absolute deltas, medians, wins and both strata. Any failed, missing, mismatched or inconclusive requirement parks the candidate. Procedural PASS and adoption remain separate. No fallback to a winning helper/case/subset or relaxed process gate is permitted.

The parent may change this proposed design only before freezing and before any C9 data. After freeze, keep every result and do not retime to seek a pass. Existing parked C4/C5/C7 decisions remain untouched.

## Scope and admission

Hold the shared benchmark lock across preparation and the fixed API screen. Every child needs fresh direct16 GiB disk and30% memory admission; keep an independent five-second read-only disk observer, exact owned PID receipts and finally wait4 settlement even after record failures. No compiler, Cargo, guest, network or metadata-payload operation is part of this Python/filesystem screen. Rust builds still require32 GiB.

One-stat validation changes the observation boundary between the old two syscalls; its source proposal documents this race limitation and retains all downstream hash/fstat/receipt/final checks. Stable path/error contracts are tested. This design does not expand those semantic claims.

Even a qualifying result establishes only this reused public validation component on synthetic26-path fixtures. Full std setup includes compiler identity, manifests and other work; full build/export/unknown-holdout claims require separately appropriate evidence. The effect may be too small to pass the retained full-process guards, and that outcome must stand.
