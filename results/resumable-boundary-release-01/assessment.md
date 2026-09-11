# Resumable guest-frame groundwork

Git `fca1e96` adds initialized reusable guest-frame backing to the VM/TLS paths.
Git `1264921` adds checked publication of resumable native cursor state. The full
workspace passes **249 tests in debug and release, with one ignored**. The first
storage-only run passed 243. All three supervised runs finished with return code
zero and unchanged frozen sources; their manifests, source archives, commands
and raw-log hashes are linked in the summaries.

Three new frame-storage tests cover retained slots, VM/TLS lifecycle transitions,
prepared descendant descriptors and failed preparation/publication. Six new
boundary tests cover descendant/ancestor continuations, positive progress at the
same PC versus zero-progress decline, exhausted one-past-code continuation,
typed terminal faults, malformed counters/descriptors/extents, guest limits and
changed backing identity. These tests model cursor/descriptor changes; they do
not execute a resumable native emitter.

The boundary validates all publication fields before changing active host
memory/frame/register extents. It checks call-depth conservation, instruction
accounting, prepared backing, guest budgets and the actual resulting top frame.
The future emitter must additionally preserve all intermediate limits, ancestor
descriptors, initialization and argument/result-copy semantics. Final-state
validation alone does not establish those properties.

No new tool was installed, runtime mode exposed or performance benchmark run.
The measured runtime remains `d664bce` / `e89de7f8`: token improves 23.6% paired
against b2, folded 4.2%, and the combined original gate fails. The next work is
resumable emission/VM integration and its execution qualification, followed by
the unchanged E2E and held-out gates.

- [Storage debug receipt](../resumable-frames-01/summary.json)
- [Boundary debug receipt](../resumable-boundary-01/summary.json)
- [Boundary release receipt](summary.json)
- [Next implementation](../../benchmarks/experiments/resumable-native-calls/EMITTER-NEXT.md)
