# Record typed relocation sites before attempting function reuse

The first census measures 178ms/460ms repeated token function work and
44ms/96ms on folded. Across token original/restored artifacts, all changes in
1,619 functions are immediates; the original source, frame layouts and code
lengths are unchanged. Two production edits change thousands of functions but
only one/five have non-immediate changes. Treating numeric-looking values as
pointers would be unsound, so the next observer starts at typed creation sites.

When the function-cost diagnostic is enabled, record immediate registers
created from compiler allocation pointers, slices, function pointers, vtables,
TLS, caller locations and the engine's errno slot. Preserve the exact original
value, relocation category, relative offset and session-local target identity.
`GlobalAlloc::TypeId` provenance represents numeric hash bits and must remain
unmodified. Ordinary integers that happen to equal guest addresses stay exact.
Direct calls and function indices remain unchanged by this experiment.

After the existing local passes, match annotations against their unique
immediate definitions. Reject missing/duplicate/mismatched annotations instead
of guessing. Build a separate diagnostic template by replacing only the typed
pointer word with its relative offset; keep slice lengths and other bits.
Include site/category/offset in its hash. Reapplying original bindings must
recover the exact original function bytes. Never rewrite the executable
program, reorder allocations, merge identities, skip checks or reuse outputs.
All observations retain explicit bounds and a completed artifact binding.

Qualify reconstruction and non-pointer controls, the original pointer-wrap,
static, TLS/HashMap, caller/function-pointer and TypeId assertions, and exact
retained/disabled/enabled artifacts. Then replay the original token/folded edit
histories once with the matching preselected restoration reference. Compare
cost-weighted template repetition to raw repetition; all prior timings remain
instrumented diagnostics. Cache feasibility still requires compiler dependency
tracking, symbolic graph assembly and measured binding/serialization costs.

The prospective cache boundary separates a function's code template from its
current compiler-resolved bindings. A template match is only an opportunity
estimate. Allocation identity, addends, packed pointers, mutable statics/TLS,
layouts, call ABI, instance kinds, target/options and compiler query dependencies
remain correctness requirements. Do not call the diagnostic hash a cache key.
