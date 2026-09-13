The bounded constant-memory extension passes all ten controls in debug and
release, including the 6,400-case byte-mask oracle. Its exact typed census covers
16 of 110 block clearing samples and 20 of 100 exhaustive clearing samples.
That is only 0.97% / 1.39% of all generated-code samples, before subtracting
alignment padding or adding future address-guard costs. Defer runtime clearing
elision. No guest command, runtime change or performance measurement follows.

The same artifact contains 5,468 functions: 669 are confined, and 1,096 / 1,150
pass initialization without / with callee-effect summaries. Eligible native
calls are 13,607,341 / 18,024,934 without summaries and 13,645,013 / 18,496,781
with them. Both modes cover exactly the same 16 / 20 clearing samples. Large
call counts do not establish a useful complete-command gain.

The extension recognizes literal FillBytes, CopyDynamic and CompareBytes
extents, plus bounded unsigned-64-bit Local-plus-constant addresses. The controls
exercise joins, overlapping copies, read-before-write, output aliases, integer
widths, oversized extents and conservative resource exhaustion. It introduces
no pointer facts through loads or name-based specialization. Whole-function
eligibility still requires entry at PC zero and guarded caller-local arguments;
confined effects alone do not establish initialized bytes.

Build/test setup takes 2.64 seconds and the typed analysis 1.53 seconds. The
coverage audit verifies 67 frozen inputs and 462 Git source bindings, including
the initial CFG analyzer's failed standalone build and its zero-coverage result.
Exact native call totals and sample joins reconcile. Full-test profiles and
sampled windows remain distinct scopes with different entropy. Original raw
artifacts, profiles and native code maps are unchanged.

The next runtime direction should address a broader remaining cost. Earlier
width packing and local-value transfer diagnostics are already negative; their
unchanged mechanisms will not be retimed. Preserve this proof as diagnostic
infrastructure rather than adding runtime guards for this small observed scope.
