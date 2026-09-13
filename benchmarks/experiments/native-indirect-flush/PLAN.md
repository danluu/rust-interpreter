# Native indirect calls composed with successor-only flushing

Start from4256b764 and the qualified opt-in indirect toola9e5116a / VM2867cde3.
The standalone indirect screen failed the wall gate (4.06% observed improvement,
4.56% A/A); successor-only flushing also failed its earlier full wall gate.
Retain both failures. This is a new composition, with no added point estimates,
changed tests, relaxed gate, or unchanged-candidate retiming.

Apply the qualified spill rule only when --jit-indirect-calls enables native
metadata. With that option disabled, retain the adopted ordinary-region rule.
A native branch may consume its last-use value directly from emitter facts;
spill only values live in successors. Tree-call tails keep their prior contract.
No metadata, indirect handle/signature checks, frame protocol or bytecode change.

Use the existing three spill fixtures, with actual resumable execution explicitly
enabling indirect calls, and all eight indirect fixtures including warmed target
limits/faults. Full workspace expectations:544 checks/profile (431 bytecode and
113 exporter),11 ignored diagnostics. Reconstruct all three retained profiled
native-indirect code captures offline; the disabled spill rule must reproduce
them exactly, and the composition may remove only the proved dead flush words.
No guest command is needed for that emission check. Then repeat applicable
strict/cache controls and original profiles with the combined immutable VM.

Only after qualification run the established40-command changed-source token
screen. Adopted/duplicate/anchor omit the experimental option; candidate includes
it. A/A envelope and wall/CPU gates remain unchanged. Full projects and parser
qualification are conditional on a passing primary. Preserve source pins,
original assertions, ordinary native controls and all restoration checks.

Use benchmark.lock with45-second admission, two Cargo workers,16 GiB build
admission,12 GiB diagnostics and8 GiB per child. Do not clean the shared target,
control peers, change the paused goal or use subagents. The three closed public
screen-cache retirement receipts are complete; do not repeat those deletions.
