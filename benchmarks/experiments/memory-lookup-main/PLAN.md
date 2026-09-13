# Integrate the five-case memory/lookup composition

All 726 expected commands and five prospective gates pass in
`results/memory-lookup-complete-01`. The timed controller is terminal, every
source is restored, and final verification covers 8,996 case and 440 harness
inputs. This integration is correctness and packaging verification, not a
repeat of that timing campaign. Historical component failures stay unchanged.

Branch from main0f11fc1 in the original worktree. Import the exact 28 changed
Rust/package files from experiment9d09183, plus the three combined launcher
files and three directly relevant Python test files. The whole Rust tree must
match the measured source, including the corrected frame-clear proof and full
register initialization. Keep the unsuccessful paired-register and guarded
indirect runtime additions excluded. Retain existing CLI defaults and explicit
options. Import the three already-qualified selection/suite/cache helpers.

The applied local manifest is `.work/memory-lookup-main-import.json`; the
committed `source-import.json` binds every imported file. Do not apply the
separate rebinding observer as part of this source integration.

Build all tools with `scripts/build_runtime_candidate.py --build-exporter`,
428 expected Rust tests per debug/release profile, two Cargo workers, the
existing owned host target, 45-second shared-lock admission and an 8 GiB floor.
Freeze committed build inputs. Retain the new complete-tool identity and
compare every executable with the measured f0af2e3e composition; do not label a
rebuilt exporter as the old binary. Check the integrated Python harness under
the same shared lock, then qualify strict real Cargo/cache behavior.

Use the qualified 203-command cache/native fixture suite and fresh/cached
compiler-identity fixture. For actual projects, export and execute original,
wrong, first valid edited and restored source states for all five completed
cases with the new tool. Compare bytecode, catalogs and original assertion
outcomes against saved candidate observations. Preserve current guest flags,
limits, two Cargo workers, prepared workers and source-restoration controls.
Use fresh owned caches and stronger large-cache admission, never write through
the completed comparison's caches. Publish only private aggregate evidence.
Record these as correctness observations, not a new performance result.

If the rebuilt VM is byte-identical, reuse its existing exact profile evidence
with explicit hashes. Otherwise qualify the seven saved selections, nine
suite commands and three exact current profile replays before merging. A new
exporter identity needs actual export qualification in either case.

Stop on unexpected outcomes or provenance/admission failures; preserve failed
commands and repair their concrete cause without altering completed results.
No other own build, test or profile runs concurrently. Inspect the independent
disk sampler, preserve other sessions and do not start another cleaner. Merge
and push verified source plus its usage/results to main, then continue with
the separate binding-cost investigation guided by the measured 124 ms token
rebinding cost and 3.077 s VM stage.
