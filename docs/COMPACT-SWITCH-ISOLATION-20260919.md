# Isolating compact switch emission on the adopted VM

The prior compact-switch/session/indirect/readonly/successor composition was
parked after its private rg-aot wall guard failed. The next experiment changes
only switch emission on the adopted fca687eb runtime. Three Rust files differ:
jit.rs, jit/compact_switch.rs and jit/compact_switch_tests.rs. The current
compiler/exporter/wrapper are retained. This is an experimental branch; main's
peer compiler and diagnostic changes must be preserved during any integration.

Seven focused checks pass in debug and release. Full workspace qualification
passes 615 Rust checks in each profile (13 ignored) and 446 Python checks
(22 skipped); setup took 109.079 seconds. All are independently closed. The
retained normal VM hash is
da0cc6b3a59dab092ae1e0ed71ccf1067f232277d362958bd871a365ce7ba6bd.

The first historical semantic replay passed its original test assertions but
stopped at an 18-instruction discrepancy: 15,849,531,264 versus 15,849,531,246.
The complete saved per-PC profiles localize the difference to
fre_target_features::macos::detect_aarch64 and its integer query helper.
Two formerly failing queries now succeed with value zero on the current host:
hw.optional.arm.FEAT_FAMINMAX and hw.optional.arm.FEAT_LUT. A zero value still
leaves the features disabled, but the helper executes a different path.

A separate, prospective current-host comparison runs the byte-identical adopted
VM. It exactly matches the already retained candidate execution, including every
logical PC, memory peak and entropy use. One adopted/candidate pair for each of
the other two original workloads also matches exactly. All three have the same
18-instruction historical difference. Five fresh executions and one retained
execution are accounted for; no candidate case was repeated to erase a failure.
Host facts are recorded before and after, and complete native maps are checked.
This qualification and the historical failure are independently closed.

This establishes semantic agreement on the current host, not a speedup.
Diagnostic entropy replay is confined to these checks; acceptance timing uses
ordinary execution. Next: install only this VM with the adopted frontend, then
run the original 40-command changed-source primary with native/adopted/A-A/anchor
arms and unreachable type/borrow failures before any guest workload. The complete
regression campaign remains required before adoption.

Evidence: `results/compact-switch-adopted-focused-01`,
`results/compact-switch-adopted-workspace-01`,
`results/compact-switch-adopted-profile-01` (preserved failure), and
`results/compact-switch-current-host-01` (exact current-host qualification).

The complete primary is now independently closed and **failed**. All40 commands,
12 original tests per execution, wrong-edit outcomes, exact artifacts/catalogs,
source restoration and both actual strict controls pass. Candidate/adopted
median wall is1.0075768713, A/A0.0341175247, sum1.0416943960. CPU is1.0078635049,
A/A0.0155656032, sum1.0234291081; the separate CPU<=1 requirement fails too.
Candidate/ordinary-native wall is1.6956241352. The small observed slowdown falls
within control variation; this is failure to demonstrate improvement, not a
causal regression claim. No runtime adoption or unchanged timing retry follows.

Installation02 is closed under key
5c78115d5ce0888367256b35fc9543e21a0964f70fab6cd77420db4b7f86fe19.
Installation01's historical-schema admission failure is retained; it created no
tool or raw directory. The corrected installer verifies that older closure's
explicit logs and Git/retained bindings. The primary protocol passed17 controls
and is independently closed. Full public controller drafts were prepared during
the primary, but their qualification and every later guard are cancelled before
execution. They retain the original seven-arm154-command ordinary-VM schedule.

The diagnostic code reduction is0.77%/0.72%/0.83% across the three original
profiles; the real edit history gives no latency benefit. Preserve this negative
result and prioritize a larger execution or lifecycle cost. Reuse the closed
adopted df4006 native captures and fine cost censuses before collecting more
samples. Small switch emission, generic address selectors, register cleanup,
frame clearing, and scalar private effects already have negative or low-coverage
evidence; a new experiment must address a distinct mechanism.
