# Native counters and successor-live spilling

Base: c6aecbcb, adopted tool35df4077 (VM f0e5f2ea). No branch-selector,
budget-fusion, wider ABI-copy or cached-return change is included.

Retain calls/returns in v29.2d across internal resumable edges. v30=[1,0]
and v31=[0,1] make each update one wrapping vector add. External entries
load exactly the adjacent two u64 State fields and initialize constants;
every return_to_vm publishes exactly those fields before restoring the host.
Resume/internal entry labels skip initialization. Ordinary and native-tree
modes remain outside this counter mechanism. Audit the existing v0..v7 copy,
v0 population count and d16 guarded-address uses. No generated resumable code
calls a host function before returning to the VM. State layout stays unchanged.

Compose the previously qualified successor-live flush rule; ordinary branch
operands remain available in facts/cache after flushing, while native-tree
call tails retain their conservative rule. Keep independent test-only switches
for exact historical reconstruction and per-component code accounting. Candidate
behavior is the default in all production and ordinary correctness builds.

Before timing: independent assembler encoding control; native counter leaves
with wrapping, unaligned State, sentinel bytes, vector clobbers and repeated
VM entries; existing full debug/release workspace and all-budget fault/TLS/
copy/profile/ABI controls; exact reconstruction of both adopted saved captures;
account separately for counter entry/update/exit changes and dead flush removal;
119 strict/cache commands; three exact entropy-bound original-test profiles,
including unchanged native calls/returns, entries, logical counts, memory and
entropy; primary harness. Preserve16 MiB capacity and two Cargo workers.

Run one fresh40-command changed-source token screen against the adopted tool.
Retain the predeclared wall+CPU A/A gate; failure ends this candidate's timing.
Only a pass permits the full five-workload comparison and114 parser controls.
No tool adoption from static counts or the short screen. Setup timing is
recorded by complete tool key. Serialize substantial work on benchmark.lock
with45-second admission; build admission16 GiB, other phases12 GiB, child8 GiB.
Never control peer processes, caches or worktrees. The saved goal stays paused.
