# Runtime work state — 2026-09-18

Manual optimization continues indefinitely; saved goal remains PAUSED. No goal
tools, subagents, peer process/session control, AWS activation or browser work.
Root owns runtime experiments; compiler/Cargo/application admission belongs to
other sessions. User suggestions unchanged SHA
4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f;
disposition docs/SUGGESTIONS-REVIEW-20260913-1245.md.

## Current result and next work

NO ACTIVE EXPERIMENT. First actual template-session primary is CLOSED and FAILED:
source756f304d, supervisor8562/controller8796, closure90499/90502. Forty source-build
commands, five modes, eight states,114 original parser tests/command, plus two
real strict type/borrow controls. Wall ratio1.011019314 + A/A.038794140 fails;
CPU.986869804 + A/A.028475789 passes. Cached/session-off wall.947186741. Keep adopted
runtime; no unchanged retiming or larger comparisons.

Cost observer4939191e ran10982/11015, CLOSED23706/23716. Reads20 retained valid-edit
reports; no compiler or guest run. Session client outside-request median31.1ms,
server outside-worker43.1ms, launcher post-execution23.4ms versus baseline10.7ms.
These intervals overlap and differ in scope; they do not attribute fsync cost.
Next material candidate: reduce redundant artifact hashing, validate an immutable
Program once/request, and use completed writes/flush like ordinary reports.
Keep strict checking, exact executed-byte binding, pre-execution reservation,
fresh guest/native owners, no retry, full lifecycle accounting and original gates.

Branch experiment/cross-program-template-session-20260918. Last primary result
pushed14d5886a; cost observer source4939191e and results about to be committed/pushed.
Publication worktree .work/publication-main clean416c4fc2; origin/main56501d24 adds
peer proof-snapshot work. Fast-forward before publishing; never force.

## Resources and workflow

Serialize substantial work with .work/benchmark.lock,45s admission, two workers.
Only build target .work/fixed-frame-clear-combined-build-01/target; never clean.
Build floor max(14GiB,8GiB+2*allocated target), analysis12GiB, child/closure8GiB.
Parser primary requires24GiB initial headroom and16GiB allowance; lastfree22GiB.
Do not lower gates. Healthy independent cleaner29541 is user-owned; read-only
status via /usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status.
Closed owned-cache retirement25b63a31 already removed25,502 intermediates;
all13,654 protected hashes unchanged. Do not repeat. Retain all old binaries,
artifacts/catalogs/proofs/sources and closed endpoint directories.

## Runtime identities

Adopted source fca687ebac0ea9374a1426addd01169fe707f608;
tool df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62;
VM 6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf;
exporter cf4b3499912506b9ebaed30e6f84e250fccba2d343558dd8cccc847e8a0be96d;
wrapper45bca4f272e994bff2564c8f5ccbd7f0d2e52cd4235a3105b4af5764e8ed7fc5.
Qualification results/scratch-scalar-main-qualification-01/summary.json:
608Rust/profile13ignored,121strict,726five-project commands,both88parser guards.
Selected test bodies only; full application threading/unwind/OS support incomplete.

Failed experimental session tool9f7aa601253a6817745070cf16a5122282d4fd9f70b33a14b625ee7a09a4a30b;
VMd84f7bc7b125ff5eaa15407ec2e5f80edb4180ca07ac8caf52a2132bad05a7e7;
serverc17f9eeb1b022f62ba5149cc425a2bbc9a67d0edca1f7e2bbc7aa8cfe6b8110b,
retained .work/cross-program-template-session-client-01/release-rust-interp-template-session.
Same adopted exporter/wrapper. Actual parser-client16commands/1,824 tests with
17,076 exact verified hits passed before primary. No runtime adoption.

[Previous full state](docs/history/STATE-20260918-before-session-request-costs.md).

Request-cost candidate53268501 passes qualification82459/82542:442Python+22skip,
651Rust/profile+16ignored, default VM build,24 owned sessions/46 client commands
allreaped. Closure35786 inprogress/check before further stages. Mainf978bac7 pushed
closed firstprimary+costresults preserving peer56501d24. Branch now
experiment/session-request-costs-20260918. Optional exact failedprimary-cache
retirement prepared but UNSTARTED because freeheadroom recovered to~26GiB.
Next16actualsavedparser suites using new VM/server, everyhitverified; thencompose
with unchangedadoptedexporter/wrapper and materialcandidate primary02.

Qualification CLOSED35786/35823, all464 frozen inputs verified. Parser replay
sourcee2ac242a ran40692/40695:16commands/1,824actualtests, alloutcomes andverified
hits match; kernelCPUreconciled. Closure45128 pending/check. Nextcompose closed
VM200148cd93a412b9b323121d67632e335b94f1a5917763e1a1d3dee489baad4c andserver
e39cda827ba050869370e93500a281c543d248778c0128efd7fb4422931920a0 withadoptedtools.

Parser replay CLOSED45128/45132,16,322 verifiedhits. Install78737879 completed
54928/54931; closure56368 pending/check. Same adoptedcompiler/exporter; noadoption.
Primary02 reuses unchangedaccounting/schedule/controller/gates with only new
closedcandidate prerequisites. Need24GiB initial and8GiB perchild. Optional
cache-retirement remainsUNSTARTED; currentfree~26GiB. Freeze candidate source,
controllers and plans through complete primary closure.

Primary02 source4533aa53 completed60442/60445, all40sourcecommands and2strict
controls pass; PERFORMANCEFAIL wall.982134251+A/A.036901385=1.019035636;
CPU.961514387+.021485469=.983000. Cached/offwall.999367745,CPU.974262244;
cached/nativewall1.306254340. Do notadopt/retimeunchanged orstartlargercomparisons.
Closure11132 running/checkterminal. Allsource restored, sessionsreaped; NOACTIVE
PRIMARY. Nextread-onlyretainedcostobserver. Assessmentdocs/SESSION-REQUEST-COSTS-20260918.md.

Costobserver89d9bf8f completed16586/16629,CLOSED17567/17570.20retainedreports;
clientoutside4.75ms/postlauncher11.72ms; remainingserveroutsideworker38.92ms,
workerprepsum35.62ms/testcompilesum146.88ms (overlap;notCPU). Noactiveexperiment.
Nextboundeddiagnosticonlypreparationphases/exactdeclinereasons onactualsaved
suites; oldgiantreducerordinarydecline23.9ms/worker stillunexplained, do notassume
16MiB. Newmaterialcandidate follows measuredcause. OptionalcleanupUNSTARTED.
