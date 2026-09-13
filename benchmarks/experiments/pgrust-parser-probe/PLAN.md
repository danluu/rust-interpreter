# Broader pgrust developer workflow: prospective support probe

Static inspection only; no build, guest execution or timing claim yet.
The current pgrust performance guard is only the hashfn crate's four tests.
Keep its historical result and do not describe it as a database workload.

At pinned pgrust38d2517d3e09168a8fe222837730d435238ff358, gram_core has about
773KB of Rust source. Its existing tests.rs contains113 #[test] functions,
and tests_dump.rs contains one additional tree-parity test, with no static
ignore/should_panic annotations. Confirm the actual registered target set via
native libtest before claiming114 tests. Its parser constructs SQL syntax trees,
uses the production scanner/arena/node crates, and the parity test compares
against vendored reference vectors. Do not modify assertions or replace any
production behavior. scan_fgram has22 existing scanner tests as an additional
coherent target; parser_driver is smaller and has a should_panic test, so it is
not the first unfiltered-support probe.

Both gram_core and scan_fgram tests already create a leaked per-test-thread
MemoryContext to avoid concurrent context-drop races in the project's pool.
Preserve that source. Prepared custom isolation creates fresh guest state per
test and remains explicit; native libtest retains its default threading. Do
not add fake threading, unwinding or project-specific runtime shims. The parser's
actual reachable allocator/TLS/formatting/table paths need real qualification;
static inspection does not establish support.

After the active guarded-runtime decision and any passing-candidate integration,
reserve resources and run an original-source native --lib test command in a
fresh owned cache with pinned Cargo/rustc, --locked --offline and two jobs.
Record the executable, registered test set, command identity, assertions and
source/tool hashes. An original native failure is a baseline failure; stop
before source edits and retain it. Then use the normal custom launcher with
strict checking, the qualified tool and complete same-target test selection.
Do not exclude failing tests after observing custom support failures. Retain
coverage and diagnose a general engine limitation if one appears.

Run the support probe before declaring new timing/edit gates. If the entire
target works, choose production-parser edits whose wrong form is detected by
original tests, freeze the real edit history and matched native/custom settings,
then measure complete changed-source commands. Include first-command and warm
edited costs separately. This adds coverage; it does not retroactively replace
any adopted regression guard or count an unchanged Cargo invocation as a speedup.

First inspect the dependency/build cache estimate and read the independent disk
sampler. Keep the shared45-second lock admission, eight-GiB floor and bounded
concurrency. Do not start this probe concurrently with the active Nushell run,
a main-integration qualification, or any other task-owned substantial command.
Do not change other sessions' sources, caches, tools or processes.

The pinned pgrust profile.dev sets debug=line-tables-only, unpacked split
information, and incremental=false. The initial support probe must preserve
those project defaults. If support succeeds, future warm comparisons must
explicitly distinguish the project-default control from matched
CARGO_INCREMENTAL=1 native/custom controls. Function-cache auto can behave
differently when compiler incremental state is disabled. Do not attribute a
project profile choice to a universal engine advantage, or mix incremental
settings between native and custom timing arms. The parity vectors are embedded
with include_str!, so that test's reference-input loading needs no guest file IO.

## First probe schedule

Require the passing complete guarded/main tool qualification. Freeze the source
pin, all tracked project files, executable tool digests, launcher helpers and
probe plan before running. Admit16GiB initially and recheck8GiB per command.
Run exactly one original-source native `cargo test -p gram_core --lib` with
JSON artifact messages, no filter, two Cargo jobs and default libtest threads.
Verify114 passing, zero ignored/filtered tests and one exact selected target
executable. Then run those exact114 bodies using the normal custom launcher,
prepared isolation with two workers, default profile settings, explicit strict
options and the exact qualified tool. Instruction/allocation limits remain
100G/150,000 per test. These two commands establish support, not timing gains.

Stop after an unexpected native or custom outcome, retaining every command and
source digest. Do not silently remove tests, change assertions, retry for a
faster result, or emulate missing OS behavior with test-specific shims. New
general runtime fixes require their own qualification and a new support probe.
A profile/default limitation remains explicitly distinct from an engine bug.
