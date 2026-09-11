# Explicit unavailable foreign calls: first fre pilot

The option adds **zero runnable bodies** in this first real-project pilot. All 61 selected ordinary tests previously blocked by Darwin semaphore calls now encounter `catch_unwind` in Rust thread cleanup during export. No new native/JIT execution replay was run because none of those 61 bodies produced a program.

The complete 389-body collection still lowers 231 and blocks 158. All 231 retained programs are byte-identical to the previous deterministic collection and use the same VM binary. Their previous execution evidence is reused by identity; this pilot does not claim 231 fresh executions. The new first blockers are 111 `catch_unwind` intrinsics and 47 wide-pointer comparisons. First-error counts do not establish that fixing one issue enables every body behind it.

The option passes 49 focused checks: cold and executed external boundaries, argument evaluation, actual leaf inlining, strict uncalled type and borrow errors, unchanged/reverted configuration and source, mismatched metadata, known-primitive signature rejection, and retained audit execution. Two initial fixture failures did not exercise actual inlining: a conversion call and then the whole-program growth cap prevented selection. Their logs and fixture versions are preserved; the final test asserts inlined trap context in both engines.

This experiment is disabled by default and has no performance qualification. It never invokes an unavailable host function or fabricates a return value. The next decision must address the newly exposed call boundary or reject the option; it cannot count shifted export errors as added execution coverage.

[Focused checks](../unsupported-extern-focused-01.json), [collection](../lowering-audit-fre-cold-extern-01/summary.md), [previous execution evidence](../audit-execution-fre-export-order-01/summary.md), [retained JIT comparison](../paired-jit-local-fill-corpus-02/summary.md).
