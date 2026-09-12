# Isolated suites after production edits

Compare three complete commands: native compiles the selected library test
target once and runs each exact test in a separate process; fresh JIT exports
the batch once and constructs a new JIT for each test; prepared JIT exports
the identical batch and shares code while giving every test fresh guest state.
Both custom modes use the same immutable tool built from 5b3268c (key 5b26d967).
No cached code survives a source edit. Ordinary libtest batches already share
code and mutable globals, so prior batch timings are not interchangeable controls.

First run pgrust's four hashfn tests with one cold original, one wrong production
edit, five cumulative real edits and a final restored-source rebuild. Use the
existing workflow cases, native repository profile, two workers in all modes,
strict checking, resumable calls and persistent registers. Each state includes
an independent Cargo-check control. Every original test must execute exactly
once per mode. A wrong edit must fail in an assertion, with matching test
outcomes across native/fresh/prepared. Missing tests, skipped tests, compiler
errors and resource-limit failures fail qualification. Require identical custom
bytecode and unchanged test source; preserve exact suite reports and hashes.

Then run the token-phrase and folded-literal-trie fre workflows with the same
protocol and each workflow's previously qualified MIR/export/runtime limits.
These distinguish a compute-heavy three-test suite from eighteen smaller tests
with shared callees. Record build, execution, preparation and per-test compilation
costs, wall and child CPU. Token randomness stays natural in complete commands;
the separate recorded-input pilot already establishes exact execution equality.
Do not require deterministic logical instruction counts from different random
inputs. Do require identical original assertion outcomes and artifact hashes.

These are functionality qualifications and descriptive five-edit measurements,
not default-promotion gates or a general speedup claim. Report paired ratios and
absolute complete-command times even if prepared loses. A later repeated
comparison must be declared separately before claiming a latency improvement.
Keep the option explicit. Nu/Ruff and private rg-aot coverage follow after this
public path is usable; full libtest ignore/should-panic/unwind/thread behavior is
still outside this runner's scope.

Use the shared lock with at most a 45-second wait and an 8 GiB floor before each
child. Require 9 GiB before admitting pgrust, 10 GiB for each fre run and assess
the larger targets separately. Freeze scripts, tools, plan and source pins.
Retain incomplete attempts; retry only after fixing a demonstrated correctness
or infrastructure failure, never to improve a measured ratio. Raw records stay
in .work; publish compact assessments and qualified source changes.
