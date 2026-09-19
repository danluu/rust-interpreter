# Manual runtime optimization checkpoint — 2026-09-19

Indefinite user task; saved goal PAUSED. No subagents, peer process control, new
AWS/billing/browser action. Own root and .work/publication-main only. Root branch
experiment/heap-layout-table-20260919. This task optimizes the custom interpreter/
AArch64 JIT with strict Rust checking and original changed-source end-to-end gates.
Installed adopted df4006 remains unchanged. See RUNTIME-NEXT.md for immediate work.
Full preceding checkpoint: docs/history/STATE-20260919-before-heap-profile.md.

## Current candidate and closed qualification

Feature heap-layout-hash changes only exact live-allocation metadata from BTreeMap
to standard seeded HashMap. The ordered free-range tree, lowest-address first-fit,
all allocation/reallocation/error/budget/zeroing logic and all guest JIT emission
remain unchanged. Default feature OFF. Runtime source d15b8db4; relative to adopted
fca687eb only bytecode Cargo.toml, heap.rs, heap_layout_reference.rs and tests differ.
The reference is the byte-identical adopted heap.rs, test-only. No prior failed
runtime candidate is composed. Latest closed samples have73/155 heap-context self
samples (partial diagnostic windows, not predicted speedups).

Focused01 source1f89038b passed16 heap tests/debug+release (including128000 generated
operations/profile) and3 C allocator tests/debug. Controller then failed because
its narrow filter missed the separate3 budget controls. CLOSED terminal1 preserved.
Focused02 sourcef0aad237 timed out45s before any child/raw; CLOSED admission failure.
Focused03 sourcec4fae859 supervisor98245/controller98250 passed missing debug3 and
all release6; independent close73158. Combined16heap+6C/profile; no prefix rerun.

Workspace01 sourcebe946738 supervisor9423/controller9466: Python446pass22skip and
Rust618pass13ignored each profile ALL passed. Before VM build it refused disk:
26305503232 free <26629357568 required. CLOSED3888terminal1; preserve all3children0.
Workspace02 source33fa2a4b supervisor67239/controller67244 reverified/reused those
3commands and built only VM (0.034s), retained .work/heap-layout-workspace-02/
rust-interp-vm hash8705a17ea9b2d909d834fdc1850835d18f08b596772dc112a817262cb3472e02.
Independent close85946 passed. Full source/script/test bindings unchanged.

Next heap-layout-profile01 requires3 original fre assertions against the CLOSED
compact-switch-current-host01 adopted profiles, same host/entropy/tapes/catalogs.
Exact PC counts15849531264/13363262210/4291122869, guest memory, entropy, generated
native bytes and maps (only PID/arena base differ). Reuse exact qualified observer.
UNRUN. Then explicit heap-layout-install01 composes retained VM with adopted
exporter/wrapper, revalidating closed121-command strict/cache frontend proof.
Then heap-layout-screen-protocol01 (17controller controls), and original40changed-
source token primary including2strict type/borrow failures. All existing wall/CPU/
A/A gates and complete held-outs remain unchanged. No runtime adoption/timing yet.

## Resource and publication contract

Python /opt/homebrew/bin/python3. Shared .work/benchmark.lock45s;2Cargo/testworkers.
Shared .work/fixed-frame-clear-combined-build-01/target NEVER clean. Build floor
max(14GiB,8GiB+2*allocated target) EACH compiler child; last26629357568. Analysis12GiB,
children/closure8GiB,fre16GiB,parser24GiB,Nushell66.55GiB. Fresh checks mandatory.
Read-only independent cleaner status: /usr/bin/python3
/Users/danluu/dev/disk-cleanup-monitor-20260912.py status. Never repair/control it.

Latest storage: closed-register-census-compression01 sourceb9706ad7 supervisor54867
finished0; independent readback passed9 exact publicfreJSONs421093376→30937088bytes,
390156288 recovered. Published main3bea799d. Before VM free26689052672. Plaintext,
mmap,required metadata and native birthtime exact. NEVER replay any inventory.
Earlier remaining-artifact-compression02 CLOSED64files/1.34GiB, main9e214d49;
public-cache-bytecode-compression02 CLOSED55files/1.23GiB, mainda13cab4; reservation
retirement01 CLOSED3191cachefiles/2780protected hashes, main8e161832. Historical only.

Publish only explicit reviewed paths through .work/publication-main, fetch/ff
preserving peer commits, commit/push HEAD:main. Never force or merge full experiment
branch. Main3bea799d includes latest storage. Runtime candidate stays branch-only.
Suggestions.txt unchanged/untracked SHA4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.

## Closed negatives — do not recreate or retime

Frame pointer-slot proof adds2eligiblefunctions but ZERO new clear samples;
local overwritten writes ZERO current1933/1429samples, older typedcensus1/1651,
2/1439. Both PARKED and published. Broad/conditional demand-region JIT already
implemented and failed token/parser gates. Branch-budget reservation40commands
correct but wall.991718334+AA.042723150 fails, CPUpasses; parked, no unchangedretry.
Compact switches, runtime composition, wider stores/registers, frame clearing,
whole-call inline, private/readonly scalar, cold fault tails, emitter workspace/
templates and general addresses have extensive closed negative history. Search
all historical PLANs/results before choosing another mechanism. Compiler/Cargo
work belongs to peer session; preserve ownership. Full history in archived STATE.

Profile01 sourced471f5ca supervisor94446 FAILED preflight, no raw or guest: copied
import still pointed to branch-budget-native-observer. Independently closed.
Profile02 fixes exactobserverpath, bindsfailure, allgatesunchanged. Install/screen
require02. VM/sourcequalification unchanged. Main3bea799d confirmedpushed.

Profile02 source520dd4e6 supervisor12779/controller12920: guest0 returned0 with
exactPC/memory/entropy/maps; raw-byte gate FAILED because427scalarCalls embedASLR
addresses (854words). FailureCLOSED withallgeneratedevidence via c9f47fc3 closer.
Newnativecomparison01 source9cd906dc supervisor76716 passed9adversarialcontrols,
verifiedall427targets exactlyarena+recordedcallee, allothernativebitsexact. Saved
blockreused, no guest. Independentclose68632passed. Profile03 continuationregistered
heap-layout-profile-resume/qualify.py: retainblock, executeONLYmissing2guests.
Install/screenrequire03, explicitrelocationequalityflag; performancegatesunchanged.
No runtime/buildchanges. Nextcommit/push thenlaunch03andindependentclose.

Profile03 sourced5ebdf1a supervisor95827/controller95839 finished0; independent
close31185passed afterpeerlockreleased naturally (earlierclose16705timeout only).
All3originalguests qualified:427/532/21scalarrelocations exact, allothernativebits
identical. Two newguests+retainedblock, no rerun. Next heap-layout-install01
install.py (explicittoolonly), --close; then heap-layout-screen-protocol01 and
--close; original40source-editprimary. All registered, no timing yet.

Install01 source830e1507 supervisor43214/controller43219 finished0; close58897
passed. Explicitcandidate da1779094da6a44c2ff63cae3767e18407050a63f54380465a9fb7fb51d70db1,
VM8705a17e plusbyteidenticaladoptedexporter/wrapper. Revalidated121frontendcontrols.
Defaultunchanged. Fullheap-layout-guards registeredconditionalONLYonclosedprimary
pass, candidatekeypinned. Nextprotocol17controls beforeoriginal40editedcommands.

Screen-protocol01 sourcee172b1b3 supervisor58386/controller58391 finished0;
17controls(7accounting+5commands+5controller), close85692passed. Nextoriginal40-
commandprimary heap-layout-screen-token01; freshfree~24.35GiB, floor16. All
source/diskfailureprefixespreserved, no timingyet. Fullguardsunrunconditional.

PRIMARY FINISHED/CLOSED: source6801f0bd supervisor72152/controller72195,
independentclose85882passed40commands+2strictcontrols,12originaltests. Wallratio
.981239792+AA.051989623=1.033229416 FAIL;CPU.979778617+AA.040559047=1.020337664pass.
PARKheap candidate, no unchangedretry; allunstartedfullguardsCANCELED. Default
unchanged. Nextpublishclosedexperimentexplicitpaths preservingpeer97076a30,
thennewbranchrestoreexactadoptedbytecode beforeofflineallocator-exit scope.
No newruntimebridge admitted without saved dominant-test scope evidence.

NEW ROOT DIRECTION: branch experiment/allocator-exit-scope-20260919; restore
EXACTfca bytecode (4files revert), no heapfeaturecomposition. Main6165c6d1 pushed
allheapqualification+closednegative, preservingpeer97076a30. Newoffline
allocator-exit-scope01 registered; no guest/build. Preliminaryadoptedprofiles count
885372/1572514/74906 allocator interpretedops; currentnativeboundaryself39/33,
otherhost27/32, heap73/155 notsavedbybridge. Need exactallocation-adjacentgenerated
samplejoin before consideringimplementation. Sharedlock45s,12GiBinitial,8GiBcase.
Freeze source/evidence throughindependent--close. Noactiveownedcommands.

ALLOCATOR SCOPE CLOSED/PUBLISHED main1853b8ec preservingpeerb361d178. Only2/1933
and0/1429 nativeallocationadjacentsamples; deferbridge. Rootadoptedhardwarebranch
registers fresh3Ccountercontrols then12originalguestcounts with currentdf4006,
matched restoredprimaryrows38/39. No compiler/sourceedit/performanceadoption.
SeeRUNTIME-NEXT for commands/admission; old7.13xcounterratio is old49746a22.

COUNTERS CLOSED/PUBLISHED maincd4b2ab6 preservingpeer9ee4b793. All12guests,
3controls; JIT/nativeinstructions3.5647block/5.2494exhaustive, cycles2.3664/3.6374.
Processaggregateonly notspeedup. Newordinary-dead-scratch01 registerssavedcode
withinspan pureoverwrittentemporary census usingexactclosedscalarworddecoder;
no build/guest/optimization. Nineold+sevennewcontrols beforeanalysis, thenclose.

ORDINARY DEAD SCRATCH01 CLOSED/PUBLISHED main8b293640. 16controls include1000
oraclecases;22346/27009staticdeadwords but4/1933and8/1429Cast samples =>DEFER.
Newbranchadopted-es8-workflow registers current matched32sourceeditcommands
(native/custom/duplicate/check),2workers,unchangedoriginal345372comparisons.
Onlyprotocol/model/commonwritten sofar; benchmark/closer stillrequired.
Preflight1670bindingspassed, freoriginalclean; nextcommitthenprotocol6controls
withsupervisor+independentclose. ReadRUNTIME-NEXT for exactpendingsteps.


## 2026-09-19 current ES8 workflow controller

The adopted-es8-protocol-01 six command/artifact/accounting controls passed and
were independently closed after recovery confirmed terminal 0 (supervisor33455,
controller33458). No guest ran. New benchmark.py/evidence.py/close.py preserve
32 commands, strict probes, fresh library+integration native/check units, actual
prepared worker assignments, immutable snapshots and compiled restoration after
SourceEdit exits. New six controller controls test restoration, injected failure,
external-edit preservation, environment/engine identity, stale units and wrong
edit agreement. Next qualify via adopted-es8-controller-01, independently close,
then launch adopted-es8-edit-01 once. All runtime crates remain exact adopted
fca687eb. Free22.7GiB; initialfre floor16GiB and childfloor8GiB. No new toolbuild.

Controller qualification adopted-es8-controller-01 CLOSED:6 tests/1 command,
terminal0, supervisor94422/controller94425, source80e4ae85. Frozen workflow ready
for single32-command current ES8 history; no project guest yet.


## 2026-09-19 ES8 current edited baseline CLOSED

adopted-es8-edit-01:32commands+2strictprobes, terminal0 supervisor97445/
controller97448 source190e8ee9. Independent close.py finished0. Five valid edits:
pairedcustom/native1.515615wall1.832604CPU; AAmax0.018799wall0.004641CPU.
Medianscustom2.077s/native1.353/check0.531; customCargo0.787/buildready0.805/
execution1.237. Strictdiagnostics rejectedbeforeexport; everyoriginaltestoutcome
agrees, wrongfailuresincluded, bytecode/catalogbothcustomexact, source restored
BEFOREfinalcompile. No candidate/adoption. Old2.678xunmatchednotbeforeafter.
NextcurrentES8 original-tests operationprofiles/ordinarynative samples, no build.
Restoredrow31RBC3bd95d7a...32d19/catalog76f774c1...e387. Runtimeunchangedfca.

ES8workflow published mainb3cfa77d (pushverified), preservingpeeraa200d45.
New experiment/adopted-es8-diagnostics-20260919: frozenfourguestcampaign ready;
2logicalprofiles then2ordinarysinglewindow samples onrow31 retainedoriginal.
Initialsampleridentitycheckfound oldcompatibilityproofpredates indirect-option
recording; no guestsstarted. Resolvedto CLOSEDcomposed-native-sampler-protocol01
11attribution/twoCLIrejection/14retainedmapcontrols matchingcurrentsources.
No runtime/flagchange: nativeindirect remainsfalse. Newrun.py --close independently
recomputesprofilelogical/codemapderivations thenallhashes/terminal.
