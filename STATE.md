# Current state — September18,2026

Continue manual optimization indefinitely. Saved goal stays PAUSED. No goal
calls, subagents or independent model calls. Root owns /Users/danluu/dev/rust-interp.
Private repository danluu/rust-interpreter. Preserve all peer work/processes.
Push qualified work regularly; do not stop at milestones.

## Current model

Branch experiment/cross-program-template-session-20260918 (from model602bbcb2). Adopted Rust/Cargo
restored exactly atcc4e767a. The closed model branch used cfg(test) only. The new session branch exposes the
same primitive behind explicit jit-template-session; ordinary builds have no
history/relocation fields. Default preparation never attaches history.
No production runtime option/store/persistence. Later explicit fixtures and saved
suites publish/execute native code; earlier staging-only models do not.

Model01 atf624e5e7 passes8controls/profile under73219/73339, CLOSED87399/87403.
Source/controllers frozen through completed closure. Controller:
benchmarks/experiments/cross-program-template-model/focus.py. Plan in samefolder.
A checked token validates bytecode structure, rejects partial headers and binds
the exact owner. It supplements, never replaces, existing strict Rust checking.
Identity includes explicit emitter fingerprint/domain, version/target/count,
heap/persistent/scalar/test options, caller ID/full Function, direct-callee layout
and current scalar bytes/step shape/target, assertion base when used. Key stream
cap4MiB; bounded ops/registers/call sites. Trusted in-memory template cap64MiB
retained payload/slack; no allocator-RSS guarantee. Restore checks key, code/table
budgets, entries/resumes/assertion PCs and rebuilds assertions from currentprogram.
Eight controls compare exact fresh words, metadata and counters across distinct
programs, changed initializers/callee bodies, options/layout/identity mismatches,
bounds, scalar targets/step shape, invalid metadata and branches/loops. Arenas
remain absent. No production integration or timing claim.

Model02 ated624307 passes12controls/profile under15329/15332, CLOSED21816/21858.
Commitfe4dc9e3 pushed. Explicit scalar/assertion relocation ledger records exact
callee/caller PC or assertion index. Complete ordered sites, encodings, targets,
BLR, same widths, budgets and fresh assertion strings are checked. Every restored
word/metadata matches fresh staging. Other changed immediates remain key misses.

Replay01 at053c7425 passes one explicit ignored release diagnostic under82090/
82093, CLOSED97242/97246. Pushed1f8c1829. Seven actual parser artifacts compared
with original selected2391/1154 active functions. All original templates captured
within32632316/16974468bytes. Valid edits restore1221–1512/601–817 exact templates;
remaining keys miss, no matching key fails restoration. Current scalar proof
tables use synthetic addresses/ascending callee order, not actual runtime arena
or admission order; no execution or production hit-rate claim. Matching IDs
associate with27.4–38.8/18.6–31.1ms original ordinary emission. Single test-mode
key intervals about9.2–9.6/5.4–5.6ms; not end-to-end savings. Docs:
docs/CROSS-PROGRAM-TEMPLATES-20260918.md. All input/output/source hashes closed.

Populated history added at153e3057:64MiB charge, at most16384 entries, two
ordered maps with one recency entry/template. Model03 admission33104/33146 timed
out before any plan/build/test, preserved/closed at6a9a82d8. Model04 at0be791ba
passes14controls/profile under47496/47500, CLOSED63293/63296. History01 atbd00c8fe
passes70734/70737, CLOSED85095/85098. Valid edit1–5 hits worker0:
1512,2389,2389,1221,2000 of2391; worker1:817,1152,1152,601,973 of1154.
Worker0 evicts447/479/635 atedit4/edit5/restored source; worker1 never evicts,
ends2230 variants/40978712chargedbytes. No capture/emission/restore declines.
These remain fixed original numeric function sets and synthetic scalar tables,
not actual later reachability or production hit rates.

Bound Request/Emission API atfe057ce0 computes one identity and immutably borrows
the exact owner/function/options through lookup/restore/capture. Model05 passes
16controls/profile under33836/33839, CLOSED53467/53470. History02 at7102b85d passes
65170/65173, CLOSED69566/69569. All16 worker/state rows match History01 outcomes,
insert/eviction, words and charge; timings intentionally excluded. Single diagnostic
lookup/restore intervals~1.1–2.9ms/0.6–1.6ms perworker on valid edits, not E2E savings.

Native fixtures added at9f573284. Model06 under97392/97395 passed16debug controls,
failed2newnative fixtures: invalid null address0 read, including fresh-JITcontrol.
Release unstarted; CLOSED16247/16250, commit952d23de. Corrected address8 and added
interpreter oracle at504d0d76. Model07 passes18controls/profile under26529/26532,
CLOSED33109/33112, committed3a813d41. Actual distinct scalar addresses, current
callee/data outputs, instruction budgets0–20, frame1–3,memory128/4096, assertion
failure and repeated fresh guest state match freshJIT; successful values/counts
also match interpreter. These2controls deliberately publish/execute nativecode;
all earlier staged models/replays publish none. No original projectguest rerun.

Lazy context integrated at8cae5e11, still cfg(test)-only and absent bydefault.
Jit.prepare_function prepares current scalar callees first, then optional Context
uses the bound Request to restore or freshly emit/capture. Existing normal
finish_preparation publishes it. Context validates the current Program once and
shares a thread-local Rc/RefCell History. Two new controls exercise real lazy
preparation across Programs and storage-decline fallback. Model08 passes20/profile
under59303/59306, CLOSED66549/66552. Commit6aeaef0e adds workspace controller.

Workspace01 source6aeaef0e completed under81196/81199:628tests/profile,15ignored;
CLOSED98526/98529, committed3d15322b. Model09 source79a562e2 adds opt-in exact
verification before publishing every hit;20controls/profile pass70826/70829,
CLOSED94632/94643. Result/controller-metadata correction committed1dde87ef,pushed.

Real suites01 source1dde87ef passes1065/1103,CLOSED5057/5061. Controller
benchmarks/experiments/cross-program-template-model/suites.py. All16suites/1824
actual parser test-body invocations across[0,-1,1,2,3,4,5,0] match savednative
outcomes with reuse off/on. Every one of16301hits matches freshly emitted words/
metadata before publication. Wrongedit8passes/106failures,others114passes.
Worker scheduling exchanges large/small workloads onedits2/3; do not substitute
fixednumeric-ID rates. Bothhistories stay<=64MiB; worker0 ends1948evictions,
worker1 none. No restore/capture declines; eachvalidworker/state hasonekeydecline
andoneordinarydecline, exactreason not established. No performanceclaim.

NEXT: promote the qualified primitive behind an explicit experimental feature,
expose bounded caller-owned in-memory history with fresh PreparedJit owners,
and qualify normal/feature builds. Then implement an explicitly started local
execution session for real changed-source commands. Keep native words trusted
in memory, no serialized executable cache. Preserve strict frontend on every
source change, fresh Program validation/scalar proof/guest state and existing
budgets. Include transport/startup/storage/remote CPU in command comparisons,
plus session-without-history control. No production adoption until existing
primary and guards pass. See docs/CROSS-PROGRAM-TEMPLATES-20260918.md.
Saved goal stays paused.

API feature source4d6ffb93 adds TemplateHistory/TemplateStorage/TemplateStatistics,
PreparedJit::with_template_history and diagnostic verification in non-test builds.
Validation once before private constructor; no native arena/Program references in
history; Rc confinement. Four integration controls plus one verifier corruption
control are new. Native fields and input keys otherwise retain qualified design.
API01 startup46850/46853 failed because controller generation failed; no controller,
build/test/guest ran. Terminal-only audit preserve_startup.py closed it. API02 at
d9cea370 ran51249/51252; default-debug629passed/16ignored, then harness incorrectly
expected15ignored (saved-suite test is the extra one). CLOSED56860/56863 beforefix.

API03 source4e11cc65 ran62916/62919: defaultrelease629passed/16ignored,
featuredebug failed compilation because a model-only Context constructor lacked
cfg(test). CLOSED71325/71329. API04 source85d224d4 corrects exactlytwo cfg
annotations and the unexecuted feature fixture's interpreter options; verifies
those exact source deltas, preserves earlierdefaultchecks. Under81086/81089,
633featuretests/profile pass,16ignored; ordinary/feature releaseVM built/retained.
CLOSED98176/98179,commit85063118 pushed. DefaultVM95b9f15ec6dbc95d455a1b9ea6a616ad4672a8dc4978b433769d697ec4dea361;
featureVM98f5f6f567b7cfa97c5959eabbca796439fc9ae6efd59d27528c3fc45dbc9222.
These are retained experimental binaries, not adopted tools.

Pipe transport source9128e86b adds explicit rust-interp-template-session binary,
feature-only PreparedJit::with_session_inputs and owned per-request environment
snapshots (no hostenvironmentmutation). Two persistentowningthreads retainbounded
histories; freshnativeowners/gueststateperrequest. Protocol4MiBcap,4096requests,
artifact/catalog hashes, cwd,boundedlimits,create-newreports. No nativecodewire,
socket,autostart orlauncherroute. Darwin getrusage ABI read frominstalledSDK and
CPUunitpasses; later E2Edriver mustchargeactualkernelwait4totals/startup/tails.
Source files crates/bytecode/src/template_session.rs andtests/template_session.rs.

Transport01 under35927/35930 passed5featureenvironmentcontrols, thenwire2passed/
1failed: serde internallytagged unitShutdown acceptedunknownfields despite
attribute. No sessionprocessfixturestarted. CLOSED38967/38970,3ef74ebb. Correction
b1ccc5b7 uses emptystructShutdown{} and retainsnegativecontrol. LibraryRust/Cargo
unchanged; successfuldebugenvironment command reusedafterhashverification.

Transport02 sourceb1ccc5b7 passed41434/41437, CLOSED46290/46294,c4d7e8c0.
All30focusedcontrols/profile,7newcommands+1reused. Eightownedfixtureprocesses
exited/reaped normally,includingtwoexpectedmalformedprotocolrejections.
Retainedrelease .work/cross-program-template-session-transport-02/release-rust-interp-template-session
SHA48b804a80047d0c72539103a6bb813f975b0353dad146343880a30d8ce559b34.

Actual parser session01 sourceb11690f5 passes58689/58692,CLOSED61577/61580;
commitdee2416c. Controller benchmarks/experiments/cross-program-template-session/parser.py.
Twoownedprocesses historyoff/on run16suites/1824bodyinvocations across8actualstates.
Every16282hit matchesfreshstagingbeforepublication. Exactcurrentoutcomes/errors
match; wrongedit8passes/106failures,othereach114passes. Servergetrusage counters
reconcilewithkernelwait4totalswithin1msconversiontolerance. Rawenvironmenttravels
onlyintheownedpipe; storedigestonly. No source-build/performanceclaim.
Allstagecommandscompleteandclosed; noactiveexperimentnow. Keepgoalpaused.

NEXT: explicit local socket endpoint and client route for independent strict
build/test commands. Do not serialize nativecachefiles. Twoowningworkers andfresh
perrequestinputs remain. Use newprivateendpointdirectory,authsecret,actualserver
binaryidentity,protocolsequenceandboundedframe I/O; noexistingendpointremoval or
autorestart. Clientfailed/lostresponsesmustneverauto-retry. Preserveexactserver
runtimeidentity inlaunchreceipts; sourcefrontend staysstrictandunchanged. Qualify
fixturesincludingwrongidentity/extraoptions, freshenvironment,cwd,reportreservation,
serverexitandfailure-recovery beforeactualeditedcommands. Thenprimarycomparison
needsfull24GiBreservation and chargesstartup/remoteCPU (currently~22GiBfree); retain
session-nohistorycontrol andordinarynative. See transportdesign doc.

Application/OS/FFI/compiler/Cargo expansion remainspeerowned; preserveboundaries.

## Completed cross-edit investigation

Branch experiment/cross-edit-emission-census-20260918 pushed2aca4f1f. All actual
model/observer failures, inputs and successful controls preserved and closed.
Detailed IDs in [previous state](docs/history/STATE-20260918-before-cross-program-template-model.md).
Seven initial structural controls/profile, then11 typed-difference controls,
12 original-identity/layout controls and13 deduplicated-report controls passed.
Original preflight incorrectly assumed restored artifact-byte equality; closed
before comparing the actual distinct artifacts. Anchors01 exceeded64MiB report
bound before publication; closed. Anchors02 stores metadata once and is22,452,178
bytes under unchanged64MiB cap. No guest/JIT/code publication in these analyses.

Saved artifacts show data/static bytes and many immediate values shifting across
edits; edit4 changes names at682IDs and2,395direct-call IDs. Immediate-only does
not mean safe pointer relocation. Edits2/3 change one function, globals stable.
Weight01 ata3923edc passes4controls and complete retained-trace association under
99970/99973, CLOSED86457/86460 after a preserved closure-lock timeout. Original
artifact/function metadata match; no-entry functions excluded. Body/layout
candidates associate with26.9–38.3ms original ordinary emission in worker0 and
18.1–30.6ms in worker1. These overlapping/nested diagnostic intervals are not
CPU, edited-run measurements or predicted savings, nor a populated-cache bound.
[Assessment](docs/CROSS-EDIT-EMISSION-CENSUS-20260918.md).

Main publication worktree .work/publication-main is clean at2e289ddf, confirmed
PUSHEDmain, preserving peer9b1166c1/bb9ef449/cd19ee2e (and earlier296a927d/bd7e74a7). Published
closed template/model/workspace/saved-suite/API/transport docs/results/plan throughsessionparser01;
no runtime candidate. Earlier census also published.
Fetch before future publication and preserve peer commits; never force push.

## Adopted runtime and parked changes

Adopted source fca687ebac0ea9374a1426addd01169fe707f608.
Tool df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62
VM 6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf
Exporter cf4b3499912506b9ebaed30e6f84e250fccba2d343558dd8cccc847e8a0be96d
Wrapper 45bca4f272e994bff2564c8f5ccbd7f0d2e52cd4235a3105b4af5764e8ed7fc5
Proof results/scratch-scalar-main-qualification-01/summary.json:608Rust/profile,
13ignored;121strict;726fiveproject commands,both88parser guards,114compatibility.
Selected-function/test-body engine: full application threading/unwind/OS support
incomplete. Compiler/Cargo/application-admission work belongs to peers.

Emitter register workspace78176777/VM5ec0cc0e passed615Rust/profile,434Python+
22skip,121strict,exactoriginalcode reconstruction, then FAILED32-command parser
primary:wall1.058595656+A/A0.060960002=>1.119555658;CPU1.046235056+
A/A0.054013185=>1.100248241. Candidate/native1.352372254. Parked; larger commands
cancelled; no unchanged retry. Branch pushed40dc130e; result docs onmain.
Same-process shared templates also parked:wall0.999311805+A/A0.044733804fails.
Other parked demand/zero/cold-tail/scalar/composition experiments remain in the
previous-state chain. Do not retime unchanged candidates or reinterpret gates.

## Resource, ownership and recovery

- Builds/tests/substantial analysis: root .work/benchmark.lock,acquire_lock(lock,45),
  two Cargo/test workers. Build target ONLY .work/fixed-frame-clear-combined-build-01/target;
  NEVER clean it. Build floor max(14GiB,8GiB+2*allocated target),analysis12GiB,
  children/closures8GiB unless higher declared. Recheck each stage.
- Last free about21.9GiB, fluctuating. Parser primary24GiB reservation completed;
  future Nushell full comparison needs its recorded~47GiB, not a reduced gate.
- Cleaner read-only: /usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status
  Do not repair/restart/compete with it or signal/control any peer/session.
- Exact closed Nu native_lines/native/check intermediate retirements completed;
  do not repeat. Check02 recovered~1.49GiB,2,687files,9,647protectedhashesunchanged.
  Preserve sources,binaries,RBC/catalogs,raw proof,tools,private/shared/peer caches.
- No AWS activation/purchase/model/billing fallback; no browser.
- User-owned untracked suggestions.txt remains SHA256
  4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.
  Reread this turn. Dispositions docs/SUGGESTIONS-REVIEW-20260913-1245.md.
- Preserve successful commands and captures. Inspect exact receipts after any
  interruption; never infer completion or rerun successful work for bookkeeping.

Endpoint01 is prepared, not yet run: private explicit socket adapter, authenticated
per-instance requests and server executable identity, no replay. Owner stdinEOF
uses DarwinSDK poll ABI and joins workers; no process signals. New socket fixtures
cover current inputs/reuse, malformed/auth/schema/sequence rejection, existing
reports/cwd, lost response, ownerEOF and occupied directory preservation.
Controller benchmarks/experiments/cross-program-template-session/endpoint.py will
run25controls/profile under the existing build/lock gate. No client route yet.

Endpoint01 source7ce2f250 passes55235/55238, CLOSED58256/58260. All25focused
controls/profile pass. Eighteen owned fixture processes exit/reap, including four
expected protocol/startup rejections. The real socket fixture changed inputs and
verified reuse match historyoff; rejected connections preserve request sequence;
lost response leaves one reserved report; ownerEOF closes while accept is idle.
Retainedrelease SHA c17f9eeb1b022f62ba5149cc425a2bbc9a67d0edca1f7e2bbc7aa8cfe6b8110b.
No client route or end-to-end timing yet. No active experiment after closure.

Client01 is prepared, unrun: explicit feature VM --jit-template-session READY_JSON
route avoids localProgramdecode and requires prepared/resumable/two-worker catalog
suite. Privateendpoint/identity, boundedrawenvironment and report/receiptreservation
are checked; actualserverPID/SHA, CPU and hashes recorded in .session.json sidecar.
Nineprocessfixturecontrols/profile expect22servers/32VMclients, includingwrong
options/identity/modes/outputs and malformedartifact recovery. Controller client.py.

Client01 source8bf8d47a passes84597/84600, CLOSED88896/88941. Nine session
controls/profile pass,22servers/32VMclients allreaped. VM flags reject incompatible
execution, actual changedinputs work, staleidentity/privatepermissions andreserved
outputs execute no request, malformedartifact error recovers without fallback.
Actualserveridentity/CPU/result hashes persist in bounded sidecar receipts; no
credential/environment contents. No active experiment. Next launcher plumbing,
retainedrealparser throughVMclients, then fullchangedsourceprimary at24GiB gate.

Launcher01 prepared: explicit runtime option and receipt verification added after
strict Cargo; an installed clienttool is required, noauto build/server/fallback.
Full Python checks include mocked ordering/selection plus receipt tamper controls;
ordinary feature-disabled VM build planned. Retained client01 Rust/binaries are
unchanged and will compose with exact adopted exporter/wrapper under new toolkey.
Controller benchmarks/experiments/cross-program-template-session/launcher.py.

Launcher01 source45f3a09d ran16292/16295 and stopped after Python failure;
CLOSED17057/17061. All seven new session/launcher/receipt controls passed.
463discovered:439passed,22skipped,1failure/1error. Two older archive-dependent
HIR tests use a missing retired peer worktree archive path. Local exact archives
exist; investigating portable fixture binding without changing peer runtime/code.
DefaultVM build and tool installation did not run. Preserve Python captures.

Launcher02 prepared after closed01. Two test-only decorators bind archived
fixtures to currentcheckout results, preserving fixedhashes and actualrawchecks;
productioncompiler code and peerworktrees unchanged. Controller verifies exact
2line additions and allother Rust/script/testhashes, carries439passed+22skipped,
then runs only two repaired tests and unstarted defaultVM build/toolcomposition.

Launcher02 source21ee5a94 passes22894/22897, CLOSED23723/23726. Two exact
archivefixture fixes pass; effectivePython441passed/22skipped with439priorpasses
preserved. Default feature-off releaseVM built SHA0790d3a245c7132c3fcea1ca0e3667fc88c8c98da60fd959c925f8bf9c9383bd.
Installed experimentalclient tool9f7aa601253a6817745070cf16a5122282d4fd9f70b33a14b625ee7a09a4a30b:
VMd84f7bc7b125ff5eaa15407ec2e5f80edb4180ca07ac8caf52a2132bad05a7e7,
exactadoptedexporter/wrapper; serverc17f9eeb1b022f62ba5149cc425a2bbc9a67d0edca1f7e2bbc7aa8cfe6b8110b.
This is unadopted candidate only. No activeexperiment afterclosure.

Main publication now416c4fc2 PUSHED, preserving peer73171edb/f67bd00f. Includes
closed endpoint/client/launcher docs/results and qualified2line archivefixturefix
a79ea80f. Runtimecandidate remainsbranchonly. Parser-client01 prepared to replay
16VMcommands/1,824actualsavedparsertests withhistoryoff/on, allhitsverified and
same launcherreceiptverifier; serverCPU reconcileswithwait4. No sourcebuildtiming.

Parser-client01 source2a0277eb passes40244/40247, CLOSED43381/43385. All16
separateVMcommands/1,824parsertests matchsavednativeoutcomes;17,076cachedhits match
freshstaging. Exactwrong-editfailuretext matchesoff/on; serverCPU reconcileswait4.
No sourcebuild/speedupclaim. Read-only locked cachecensus saved
.work/template-session-cache-census-01.json:two exactclosed failedparser primaries
(emitterworkspace/sharedtemplates) have4.073GiB allocated eligible nonexecutables
in8owned caches. Planning guarded retirement to restore24GiB primary admission.

Closedtemplateprimarycache retirement source48ccbc49 ran74603/74606,
CLOSED82107/82110. Removed25,502exactnonexecutable intermediates from8caches in
2closedfailed32commandprimaries; logical4,319,150,643bytes, allocatedcensus4.073GiB.
All13,654protectedhashes unchanged; binaries/RBC/catalogs/proof/sources retained.
Free~25.7GiB, recheck before24GiB primary. Noactiveexperiment afterclosure.
Nextfive-mode40command primary: native,adopted,A/A,sessionoff,sessionon; two extra
untimedstrict type/borrow rejection controls in independentnamespace. Charge
startup/teardownwall and allkernelserverCPU; keep prospectiveoriginalnoisegates.

Prospectiveaccounting protocol source204e669a passes92516/92529, CLOSED20384/
20418. Seven controls test five-modebalance, kernelCPUconservation, fullsetupcharge,
falsewinsfromomittedcosts, worstA/Anoise, sessionoffcomparison and invaliddata.
Newprimarycontroller/closer/prereqs prepared under
benchmarks/experiments/cross-program-template-screen. Fortyactualsourcecommands
plus2untimedstrict type/borrow controls; requires24GiB and2workers. Fullserver
startup/tails/teardown charged; noautomaticretry orchangedgate. Sourcepin/oldnative
inventory/artifact equality and originaloutcomes preserved. Notyetstarted.
