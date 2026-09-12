# Bounded placement follow-up

The completed census 02 found 25,048,737 token direct calls whose callees are
blocked only by CompareBytes and/or the old initialization proof. Eligibility
alone does not justify implementation. Measure actual placement before proceeding.

`placement.rs` copies integrated `crates/bytecode/src/inline.rs` from `5b2330c`.
Three diagnostic policies use identical size, growth and diagnostic-string limits:

1. Unchanged eligibility/guard. Require its resulting Program to serialize
   byte-for-byte identically to the integrated library pass on both real inputs.
2. Accept CompareBytes (with complete operand relocation) and the existing
   entry-prefix initialization proof for leaves; retain the old caller guard.
3. Same eligibility, with the caller guard comparing actual runtime initialization
   requirements before/after, rejecting newly introduced whole-caller clearing.

Report exact selected original Call PCs, their original dynamic counts, code and
frame growth, and incoming calls to newly cleared callers. No guest execution or
performance claim. This is not an exporter qualification and does not install
the transformed programs. Keep the census 02 result and test-count failure intact.

If the runtime guard removes most opportunities, investigate a stronger bounded
definite-initialization proof shared by runtime and compiler before expanding
inlining. Do not weaken initialization requirements or tune the size thresholds.
