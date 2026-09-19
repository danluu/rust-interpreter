# Runtime work: local writes overwritten before observation

Continue indefinite manual optimization of the custom interpreter/direct AArch64
JIT, guided by real changed-source end-to-end benchmarks. Do not stop at milestones.
No subagents, goal tools, AWS/browser actions or peer process/session control.
Saved goal stays PAUSED. This root and .work/publication-main are our worktrees.

## Current work

Root branch experiment/local-overwritten-writes-20260919. The entire bytecode
crate matches adopted fca687ebac0ea9374a1426addd01169fe707f608. Installed/default
runtime remains df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62.
No production change is active. The new scope diagnostic is registered at
benchmarks/experiments/local-overwritten-writes; its12 controls and saved-data
analysis are UNRUN. Next commit/push then supervise local-overwritten-writes-01
using analyze.py. Freeze new sources through terminal plus independent --close.

The model follows at most128 pending local Store/Copy writes inside each exact
native region. It proposes a write only after all its bytes are overwritten,
before any observing read or potential fault/exit. Copy sources are read first;
unknown addresses (including zero-byte accesses), calls, assertions, division and
unreviewed operations are barriers. Lost capacity loses opportunities. Controls
include2000 concrete40-event traces comparing every read/barrier and final bytes
with all proposed writes removed together. The model uses rendered operations
only to estimate scope; a typed/emitter/native proof is required before runtime
changes. Existing closed1933/1429 generated samples and separate logical profiles
are reused. No build, guest execution, native publication or timing is planned.

## Closed decisions

Pointer-slot initialization is PARKED. Build01 sourceef0dbc05 supervisor97343/
controller97346 passed18debug+18release controls (6400CFG-mask and19584byte-copy
cases), built the standalone analyzer and analyzed5468functions. Independent
close53987 passed. Old proof exactly reproduced; initialization1150→1152,
confined669→671, no eligible functions lost. Coverage01 sourced3430707,
supervisor26594/controller26634 finished0, close29524 passed: both proofs cover
only1/89 and1/62 adopted frame-clear samples, with ZERO newly covered samples.
Do not implement or retime this direction. See docs/FRAME-SLOT-INITIALIZATION-20260919.md.

Branch-budget reservation2ce1d2e2 is PARKED after closed source-edit primary:
40commands+2strict controls correct; wall.991718334+AA.042723150=1.034441484 fails.
CPUceilings pass. No unchanged retry; all unstarted full guards canceled. Sources
preserved on experiment/branch-budget-reservation-20260919 atb76eb428. Root restored
adopted bytecode atb661aad3. Mainc32abc18 published failed gate and prior controls.

Earlier parked directions include compact switches, session/runtime composition,
implicit zero frames/selective repairs, wider clearing/copies/register banks,
fixed/private call ABI, whole-call inlining, readonly/private scalar extensions,
cold fault tails, general addresses, local-copy equality (26/7samples), reserved
local-copy payloads (2/2loadsamples), and small call-free loops. Do not repeat an
unchanged failed candidate or relax a gate. Long history is preserved in
docs/history/STATE-20260919-before-overwritten-writes.md and referenced documents.

## Resource and publication contract

Python /opt/homebrew/bin/python3. Shared .work/benchmark.lock;45s admission.
Two Cargo/test workers. Shared .work/fixed-frame-clear-combined-build-01/target
is NEVER cleaned. Build floor=max(14GiB,8GiB+2*allocated shared target), recomputed
before EVERY compiler child. Analysis12GiB, children/closure8GiB, fre16GiB,
parser24GiB, Nushell66.55GiB. Latest free23.64GiB; new builds are NOT admitted
without a fresh calculation. Cleaner is independently owned; status only:
/usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status.

Compression02 sourcecad71f1c supervisor87219/controller87222 CLOSED67524:
55exact public bytecode/JSON files1798995968→478756864allocated bytes, saved1.23GiB,
all hashes/required metadata/native creation times preserved. Attempt01 timed
out BEFORE inventory/mutation; closed failure is retained. NEVER replay either
inventory/mutation. Main da13cab4 publishes both attempts and qualified scripts.
Earlier exact reservation cache retirement01 CLOSED50ba66:3191compiler files,
2780protected hashes unchanged, ~1.59GiBfree; publishedmain8e161832. All earlier
closed retirements/compressions remain historical and must never be replayed.

Main publication: .work/publication-main, fetch then fast-forward preserving all
peer commits; restore explicit reviewed paths only, commit and push HEAD:main.
Never merge this entire experiment branch, force-push or overwrite peer work.
Root d9dcb02f pushed before current pending registration. Latest main da13cab4
published storage; publish closed slot diagnostic/coverage next. No activeowned
commands. Suggestions remains unchanged/untracked SHA256
4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.

local-overwritten-writes01 source00ee280a supervisor34801/controller34804 passed12
controls (2000x40concreteevents). Bothcensuses andindependentclose48205 passed,
52bindings.1501/1802candidates, ZERO current1933/1429samples. PARKED, no runtime.
Historysearchthenfoundoldertyped local-overwrite-coverage01 alreadynegative1/1651,
2/1439. Currentanalysis updatescapturedscope, NOT a newmechanism. Also broad/
conditionaldemandcompilationalreadyimplementedandfailedtoken/parsergates; don't
repeat. Main968b1472 publishesclosedslotproof preservingpeer608da6ba.
Nextreviewheapownershipmetadata: latestsavedcapturehas73/155heap-contextsamples;
exactlayoutget/insert/remove usesBTreeMap despite noordering requirement. Free-
range addressordering MUST remain unchanged. No allocatorimplementationyet.

New branch experiment/heap-layout-table-20260919. UNBUILT featureheap-layout-hash
changesonlyexactliveallocationlayouts tostdHashMap; orderedfreeBTreeMap andall
allocationbodylogic unchanged. Defaultfeatureoff. Exactfca heap.rs snapshot is
retainedtest-onlyreference.4newcontrols incl16freshmapinstances,128000seededops,
allpointers/errors/guestbytes/live layouts; focuscontroller expects16heapcontrols
and6Callocatorcontrols perdebug/release (4commands). No build/test/profileyet.
Buildfloor25700851712bytes, free25352810496: NOT admitted. Newregistered
closed-remaining-public-artifact-compression01 selectssevenclosedpublicartifact
snapshotsets (~1.8GiB); originalplaintextsha=filename=closed-evidencesha. Existing
qualifiedcompression/birthtimehelpersunchanged. No mutationlaunchedyet. Next
commit/push, supervisecompression, independentclose, freshfloor, thenheapfocus.
No activeownedcommands; negativeoverwrittenpublication mayneedpushverification.

Remaining-artifact-compression01 sourced15b8db4 supervisor10674/controller10677
FAILED beforeinventory/mutation: oldparser frozenownership value is{kind:file,
sha256}, notbarehash. ActualownerSHA exactlymatches. Closedpreflightfailure
retained; new02 normalizesonlythetwoexactformats andbindsfailure. No replay.
Main4be97e5e overwrittennegativepublicationverified, preservingpeeree68f923.
HeapfocusstillUNRUN; commitcorrectionthenlaunchcompression02 beforebuildadmission.

Remainingcompression02 source027aa15a supervisor19410/controller19413 finished0;
independentclose95238 passed64bytecodesnapshots,1912537088→475934720allocatedbytes,
1.34GiBreclaimed. Allbytes/requiredmetadata/birthtimesidentical; NEVER replay.
Free26795442176 vsbuildfloor25700851712 (allocatedtarget8555458560) admitsfocus.
Heapworkspace01 registeredUNRUN expects618Rust/profile13ignored,446Python22skip,
retainedfeatureVM; requiresclosedfocus16heap+6C/profile first. No guest/timing.
Nextlaunchfocus afterthiscommit; sourcesfreeze throughitsindependentclosure.

2026-09-19 resumed: main9e214d49 confirmed remote. Focus01 CLOSEDterminal1 after
all3children0:heap16debug+16release,Callocator3debug. Count expectation erroneous
because separate budget module excluded. New focused02 continuation runs missing
budget3debug+all6release, no repeat completedprefix. Workspace01 dependsclosed02.
No candidate guest/install/timing. See updatedRUNTIME-NEXT and continuationPLAN.

Focused02 timed out at45s sharedlock before raw/tests; independently closed.
Peer holder44851 now finished naturally; no process controlled. Readmit as03
with unchanged tests and retained02 admission receipt. Workspace requires03.
Heap-layout-profile01 registeredUNRUN using exact currenthost/code/map checks.

Focused03 sourcec4fae859 supervisor98245/controller98250 finished0; independent
close73158 passed. Newbudget3debug+all6release, retainedheap16/profile andC3debug.
Combined16heap+6C/profile complete, originalfailure andadmissiontimeout preserved.
Next workspace01 (4commands), independent--close; freeze allcrates/scripts/tests.

Workspace01 sourcebe946738 supervisor9423/controller9466 CLOSED3888terminal1.
Python446pass22skip, Rust618pass13ignored eachprofile ALLpass. BeforeVM build,
free26305503232<floor26629357568. NoVM buildran. Newworkspace02 resumequalify
rederives/reuses3passingcommands, buildsVM only. Newclosed-register-census-
compression01 selects9publicfreJSONs/sixclosedruns421093376allocatedbytes;
qualifiedhelpersunchanged. Commit, compress, close, freshadmission thenworkspace02.
Profile/installnowrequireworkspace02. No guest/timing; two new gatesUNRUN.

Closedregistercensuscompression01 sourceb9706ad7 supervisor54867 finished0;
independentclosepassed9JSONs421093376→30937088allocated,390156288bytes recovered.
Allplaintext/metadata/nativebirthtimespreserved. NEVER replay. Freshbuildfloor
26629357568,free~2669M? usefreshbytesbeforeworkspace02 (onlyVMbuild).
