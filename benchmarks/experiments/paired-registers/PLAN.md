# Paired VM-register transfers

Start from the qualified wide-operation runtime f8713aaa. Restore its exact
runtime sources before this change; the guarded-indirect candidate remains
preserved separately, with a completed failed token performance gate. Retain
the wide exporter and wrapper. No compiler, bytecode layout, checking or
register-assignment change belongs to this candidate.

Raw spills and persistent-register reloads currently issue separate 64-bit
accesses for the two words of a VM register. Use non-writeback AArch64 STP/LDP
when register indices0..31 fit the positive scaled pair offset. Keep existing
scalar accesses for32..2047, where forming a pair base would add an instruction.
At2048 and above, compute the shared full-register base once and issue a pair,
instead of forming a separate large address for each word. Both words remain
initialized and transferred; zero-high-word elision is a different proposal.

The base is the initialized host-owned register array, not guest-addressable
memory. Every register index is already validated and both words fit its slot.
No writeback, new memory model, guard removal or cross-thread publication is
introduced. The existing emitter already uses pair encodings for host-stack
preservation. Reduced emitted word count is a mechanism, not a speedup claim.

Two new tests cover encoding/count boundaries, full-width values, spills and
reloads around an unsupported operation, persistent assignment on/off and
every instruction-budget tail. Provisional host count is421 per debug/release
profile. Qualify those tests and existing exact real-program/suite/cache
controls before any new runtime timing. Current guarded-indirect folded and
pgrust guards take priority; do not build or execute this candidate while an
owned benchmark holds the shared lock. All existing frozen Python inputs stay
unchanged. Freeze a new complete-command comparison only after qualification.

Use the paired comparison to choose further work. Existing larger-register-bank
and larger-local-cache experiments found no useful benefit; this changes the
instructions that transfer the existing values, without repeating those
allocation policies. Instruction sampling may supplement the mechanism check;
complete edited commands remain the adoption outcome.
