# Private thin-pointer promotion experiment

The default scalar promoter handles private primitive numeric MIR locals.
Pointer locals are excluded by both its type gate and the default visitor's
projection context. Existing bytecode Copy/Load/Store work and the failed narrow
emitter experiments motivate investigating this earlier representation choice.

The candidate is a default-OFF Cargo feature, private-pointer-promotion. The
entire bytecode/runtime crate remains identical to adopted fca687eb; no new JIT,
interpreter, LLVM or foreign-engine path. Full rustc checking still precedes
lowering. The exporter binary digest already namespaces function-cache entries,
so feature-on and feature-off binaries cannot reuse each other's lowered code.
Verify that contract with installed binary hashes before any real experiment.

Eligibility is limited to non-argument/non-result Ref/RawPtr locals of exactly
eight bytes. No frame packing change. A first Deref projection reads the pointer
value even when the pointee is written or borrowed. Taking the address of the
pointer slot itself still rejects promotion. All other contexts follow the
existing conservative policy; a rejected local cannot be readmitted. Visit index
operands/types normally. Fat pointers, function pointers, aggregates and owning
ADT values remain excluded. Bound to4096 locals/32768 MIR events and existing
lowering/transform limits. Preserve direct call-argument, call-result, aggregate
operand, overlapping-slot and unproved bytecode-address exclusions.

Use the existing typed scalar transform, zero initialization, branch remapping
and move elimination. Record candidate and actually promoted pointer offsets
separately from existing numeric counts. No externally supplied bytecode obtains
a nonescape assumption. Tests must distinguish pointer storage from pointee
aliases; treating all projection uses as harmless would be unsound.

Qualification sequence, not yet run:

1. Recompute shared-target disk reserve. If needed, retire only exact closed
   task-owned compiler caches after independent evidence/inactivity/open-file
   checks. Never clean the shared target or interfere with peer processes.
2. Run focused scalar-promotion tests with the feature off/on in debug/release,
   including context/escape controls and interpreter/native pointee-alias tests.
   Build and retain the candidate exporter/wrapper, using the exact adopted VM.
3. Use real checked MIR fixtures for thin shared/mutable/raw pointers, loops,
   direct borrowed slot mutation, direct call operands/results, index operands,
   fat pointers and reference-to-pointer escapes. Require positive actual
   pointer-promotion counts where intended and rejection where not. Compare
   feature-off output with adopted output, and feature-on guest outputs with
   native Rust/feature-off. Check strict unreachable E0308/E0499 before export.
4. Qualify workspace/default-feature behavior and full original public/private
   test-body suites before a complete changed-source screen. Candidate bytecode
   intentionally changes: require original assertions, catalog/test identities,
   wrong-edit failures and restoration, not false byte-for-byte equality.
   The harness/accounting needs separate prequalification for this frontend
   experiment; do not reuse a runtime screen that assumes identical artifacts.
5. Freeze a complete-edit native/adopted/duplicate/candidate/anchor primary and
   all regression guards before timing. Preserve CPU, build and execution costs,
   same-run A/A variation, resource admission and failed outcomes. Do not retime
   an unchanged failed candidate or infer adoption from static counts.

No build or fixture has been run yet. Current free space is below the last
dynamic build reserve; source preparation is allowed, build admission is pending.
Two Cargo/test workers, shared benchmark lock45s, conservative disk checks and
independent closure. No change to paused goal or other sessions.
